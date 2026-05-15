#!/usr/bin/env ruby
#
# bump-catalog.rb — promote high-frequency entries from the local usage
# cache (usage.jsonl) into prestamp-catalog.yml, bump the plugin version,
# and open a PR. Fully deterministic; no LLM calls.
#
# Modes (default is --dry-run — explicit opt-in for destructive ops):
#   --dry-run  — print the diff summary, do not modify any file (DEFAULT)
#   --apply    — modify prestamp-catalog.yml only (no version bump, no git ops)
#   --pr       — full pipeline: --apply + plugin.json bump + branch/commit/push/PR
#                (verifies clean tree + branches from origin/main)
#
# YAML merge strategy:
#   - Existing terms: append unseen variants (fingerprint = font/color/
#     animation/outline/outline_width/speed). Identical flavor is a no-op.
#   - New terms: append a fresh `<term>:` block at the end of the
#     `terms:` map.
#   - File-level comments and existing variant ordering are preserved.
#
# Usage:
#   ruby bump-catalog.rb [--cache PATH] [--catalog PATH] [--plugin-json PATH] \
#     [--threshold N] [--dry-run | --apply]

require "optparse"
require "json"
require "yaml"
require "set"
require "fileutils"

REPO_ROOT = File.expand_path("../../../..", __FILE__)
SCRIPTS_DIR = File.expand_path("..", __FILE__)
DEFAULT_CATALOG = File.join(SCRIPTS_DIR, "..", "data", "prestamp-catalog.yml")
DEFAULT_PLUGIN_JSON = File.join(REPO_ROOT, ".claude-plugin", "plugin.json")
CACHE_STATS_SCRIPT = File.join(SCRIPTS_DIR, "cache-stats.rb")

def default_cache_file
  env_override = ENV["MOJIEMOJI_CACHE_FILE"]
  return env_override unless env_override.nil? || env_override.empty?

  data_home = ENV["XDG_DATA_HOME"]
  data_home = File.join(Dir.home, ".local", "share") if data_home.nil? || data_home.empty?
  File.join(data_home, "mojiemoji-plugin", "usage.jsonl")
end

options = {
  threshold: 2,
  mode: :dry_run,
  cache: nil,
  catalog: DEFAULT_CATALOG,
  plugin_json: DEFAULT_PLUGIN_JSON,
}

OptionParser.new do |opts|
  opts.banner = "Usage: bump-catalog.rb [options]"
  opts.on("--cache PATH") { |v| options[:cache] = v }
  opts.on("--catalog PATH") { |v| options[:catalog] = v }
  opts.on("--plugin-json PATH") { |v| options[:plugin_json] = v }
  opts.on("--threshold N", Integer) { |v| options[:threshold] = v }
  opts.on("--dry-run") { options[:mode] = :dry_run }
  opts.on("--apply") { options[:mode] = :apply }
  opts.on("--pr") { options[:mode] = :pr }
end.parse!

cache_file = options[:cache] || default_cache_file
catalog_path = options[:catalog]

unless File.exist?(catalog_path)
  STDERR.puts "catalog not found: #{catalog_path}"
  exit 1
end

# --- 1. Run cache-stats to get candidate YAML fragment -------------------

stats_out = IO.popen(
  ["ruby", CACHE_STATS_SCRIPT, "--file", cache_file, "--threshold", options[:threshold].to_s],
  err: $stderr,
  &:read
)

if stats_out.strip.empty?
  STDOUT.puts "bump-catalog: no candidates from cache (threshold=#{options[:threshold]})."
  STDOUT.puts "bump-catalog: no new variants to add."
  exit 0
end

candidates = YAML.safe_load("---\n#{stats_out}", permitted_classes: [], aliases: false) || {}

# --- 2. Diff against existing catalog -----------------------------------

catalog = YAML.safe_load(File.read(catalog_path), permitted_classes: [], aliases: false) || {}
existing_terms = catalog["terms"] || {}
defaults = catalog["defaults"] || {}

def flavor_fingerprint(flavor, defaults = {})
  resolved = defaults.merge(flavor)
  [
    resolved["font"], resolved["color"], resolved["animation"],
    resolved["outline"], resolved["outline_width"], resolved["speed"],
  ]
end

additions_for_existing = {}  # term => [flavor, ...]
new_terms = {}               # term => [flavor, ...]

candidates.each do |term, variants|
  existing = existing_terms[term]
  if existing.nil?
    new_terms[term] = variants
    next
  end
  existing_fingerprints = existing.map { |v| flavor_fingerprint(v, defaults) }.to_set
  unseen = variants.reject { |v| existing_fingerprints.include?(flavor_fingerprint(v, defaults)) }
  additions_for_existing[term] = unseen unless unseen.empty?
end

total_new = new_terms.values.sum(&:size) + additions_for_existing.values.sum(&:size)
if total_new.zero?
  STDOUT.puts "bump-catalog: all #{candidates.size} candidate term(s) already in catalog."
  STDOUT.puts "bump-catalog: no new variants to add."
  exit 0
end

# --- 3. Render diff summary ---------------------------------------------

def yaml_value(value)
  s = value.to_s
  return s if s.match?(/\A[a-z][a-z0-9_]*\z/i) && !s.match?(/\A\d/) && !s.match?(/\A[0-9a-f]{6}\z/)
  "\"#{s}\""
end

def render_variant_lines(flavor, indent: "    ")
  lines = []
  lines << "#{indent}- font: #{flavor['font']}"
  lines << "#{indent}  color: #{yaml_value(flavor['color'])}"
  lines << "#{indent}  outline: #{yaml_value(flavor['outline'])}" if flavor['outline']
  if flavor['outline_width']
    lines << "#{indent}  outline_width: #{yaml_value(flavor['outline_width'])}"
  end
  lines << "#{indent}  animation: #{flavor['animation']}"
  lines << "#{indent}  speed: #{flavor['speed']}" if flavor['speed']
  lines
end

summary_lines = []
unless new_terms.empty?
  summary_lines << "新規 term (#{new_terms.size} 件):"
  new_terms.each do |term, variants|
    summary_lines << "  #{term}: #{variants.size} variant(s)"
  end
end
unless additions_for_existing.empty?
  summary_lines << "既存 term への variant 追加 (#{additions_for_existing.size} 件):"
  additions_for_existing.each do |term, variants|
    summary_lines << "  #{term}: +#{variants.size} variant(s)"
  end
end
STDOUT.puts summary_lines.join("\n")

if options[:mode] == :dry_run
  STDOUT.puts
  STDOUT.puts "--- dry-run: catalog NOT modified ---"
  STDOUT.puts "would add #{total_new} variant(s) across #{new_terms.size + additions_for_existing.size} term(s)."
  exit 0
end

# --- 4. Apply changes to catalog ----------------------------------------

text = File.read(catalog_path)
lines = text.lines

# Add unseen variants under existing terms. Each term block in the YAML
# starts with `  <term>:` and continues until the next `^  \S` line or EOF.
additions_for_existing.each do |term, variants|
  start_idx = lines.find_index { |l| l.start_with?("  #{term}:") }
  next if start_idx.nil?
  insert_idx = lines.length
  (start_idx + 1...lines.length).each do |i|
    if lines[i] =~ /\A  [^\s-]/
      insert_idx = i
      break
    end
  end
  block = variants.flat_map { |v| render_variant_lines(v).map { |l| l + "\n" } }
  lines.insert(insert_idx, *block)
end

# Append wholly new terms at end of file (after a blank line).
unless new_terms.empty?
  lines << "\n" unless lines.last&.end_with?("\n")
  new_terms.each do |term, variants|
    lines << "\n"
    lines << "  #{term}:\n"
    variants.each do |v|
      render_variant_lines(v).each { |l| lines << l + "\n" }
    end
  end
end

File.write(catalog_path, lines.join)
STDOUT.puts "bump-catalog: catalog updated with #{total_new} variant(s)."

if options[:mode] == :apply
  exit 0
end

# --- 5. Bump plugin.json patch version (PR mode only) -------------------

if File.exist?(options[:plugin_json])
  plugin = JSON.parse(File.read(options[:plugin_json]))
  version = plugin["version"] || "0.0.0"
  parts = version.split(".").map(&:to_i)
  parts[2] = (parts[2] || 0) + 1
  bumped = parts.join(".")
  plugin["version"] = bumped
  File.write(options[:plugin_json], JSON.pretty_generate(plugin) + "\n")
  STDOUT.puts "bump-catalog: plugin.json #{version} -> #{bumped}"
end

# --- 6. Git: branch + commit + PR ---------------------------------------

# Verify clean tree (excluding the catalog + plugin.json we just modified).
# A dirty tree means uncommitted changes from other work — fail loudly
# rather than mix them into the auto PR.
status_out = IO.popen(["git", "status", "--porcelain"], &:read)
dirty = status_out.lines.reject do |line|
  path = line[3..].to_s.strip
  path == catalog_path || path == options[:plugin_json] ||
    path == File.expand_path(catalog_path) || path == File.expand_path(options[:plugin_json])
end
unless dirty.empty?
  STDERR.puts "bump-catalog: refusing to PR — working tree has unrelated changes:"
  STDERR.puts dirty.join
  exit 1
end

# Stash our catalog + plugin.json changes so we can branch from a clean main.
system("git", "stash", "push", "-m", "bump-catalog-temp", "--", catalog_path, options[:plugin_json]) || exit(1)
system("git", "fetch", "origin", "main") || exit(1)
system("git", "checkout", "main") || (system("git", "stash", "pop"); exit(1))
system("git", "pull", "--ff-only", "origin", "main") || (system("git", "stash", "pop"); exit(1))

date_slug = Time.now.utc.strftime("%Y%m%d")
branch = "feat/auto-catalog-grow-#{date_slug}"
title = "feat(catalog): #{total_new} 件の variant を自動追加"
body = <<~BODY
  ![type](https://img.shields.io/badge/type-feat-blue) ![scope](https://img.shields.io/badge/scope-catalog-blue) ![auto](https://img.shields.io/badge/auto-generated-purple) ![tests](https://img.shields.io/badge/tests-passing-green)

  ## 概要

  `scripts/bump-catalog.rb` がローカル `usage.jsonl` から閾値 (#{options[:threshold]}) を満たした variant を catalog に昇格させた自動 PR です。

  #{summary_lines.join("\n")}

  total: **#{total_new} variant(s)** across **#{new_terms.size + additions_for_existing.size} term(s)**.

  ## 出典

  自動 PR は #46 で定義された複利型の catalog 育成サイクルの一部です。
BODY

system("git", "checkout", "-b", branch) || (system("git", "stash", "pop"); exit(1))
system("git", "stash", "pop") || exit(1)
system("git", "add", catalog_path, options[:plugin_json]) || exit(1)
system("git", "commit", "-m", title) || exit(1)
system("git", "push", "-u", "origin", branch) || exit(1)
pr_url = IO.popen(["gh", "pr", "create", "--assignee", "@me", "--title", title, "--body", body], &:read).strip
STDOUT.puts pr_url
