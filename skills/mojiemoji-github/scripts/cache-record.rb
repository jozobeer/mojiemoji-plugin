#!/usr/bin/env ruby
#
# cache-record.rb — append a JSON Lines usage entry to the local cache.
#
# Invoked by mojiemoji-selector after rendering each snippet (catalog miss
# or otherwise) so the deterministic bump-catalog.rb can later promote
# high-frequency entries into prestamp-catalog.yml.
#
# Cache path resolution (first match wins):
#   1. $MOJIEMOJI_CACHE_FILE
#   2. ${XDG_DATA_HOME:-$HOME/.local/share}/mojiemoji-plugin/usage.jsonl
#
# The parent directory is created on demand. Failures are reported on
# stderr and exit 1 so the caller can decide whether to surface them;
# the mojiemoji-selector wraps the call in a way that does NOT block
# snippet return.
#
# Usage:
#   ruby cache-record.rb --term 完成 \
#     --font maru-bold --color 22c55e --animation poyoon \
#     --outline 9934d3 --outline-width 2 [--speed slow] [--source selector]

require "optparse"
require "json"
require "time"
require "fileutils"

# Opt-out: users who do not want their selector usage recorded can set
# MOJIEMOJI_CACHE_DISABLED=1 in their environment. Silent no-op.
if %w[1 true yes].include?(ENV["MOJIEMOJI_CACHE_DISABLED"].to_s.downcase)
  exit 0
end

def default_cache_file
  env_override = ENV["MOJIEMOJI_CACHE_FILE"]
  return env_override unless env_override.nil? || env_override.empty?

  data_home = ENV["XDG_DATA_HOME"]
  data_home = File.join(Dir.home, ".local", "share") if data_home.nil? || data_home.empty?
  File.join(data_home, "mojiemoji-plugin", "usage.jsonl")
end

options = { source: "selector", outline_width: "2" }
parser = OptionParser.new do |opts|
  opts.banner = "Usage: cache-record.rb --term TERM --font F --color C --animation A --outline O [opts]"
  opts.on("--term TERM") { |v| options[:term] = v }
  opts.on("--font FONT") { |v| options[:font] = v }
  opts.on("--color COLOR") { |v| options[:color] = v }
  opts.on("--animation ANIM") { |v| options[:animation] = v }
  opts.on("--outline OUTLINE") { |v| options[:outline] = v }
  opts.on("--outline-width WIDTH") { |v| options[:outline_width] = v }
  opts.on("--speed SPEED") { |v| options[:speed] = v }
  opts.on("--source SOURCE", "selector | direct (default: selector)") { |v| options[:source] = v }
  opts.on("--file PATH", "Override cache file path (otherwise $MOJIEMOJI_CACHE_FILE or XDG default)") { |v| options[:file] = v }
end
parser.parse!

required = %i[term font color animation outline]
missing = required.reject { |k| options[k] && !options[k].to_s.empty? }
unless missing.empty?
  STDERR.puts "missing required flag(s): #{missing.map { |k| "--#{k.to_s.tr('_', '-')}" }.join(', ')}"
  STDERR.puts parser.help
  exit 1
end

flavor = {
  font: options[:font],
  color: options[:color],
  animation: options[:animation],
  outline: options[:outline],
  outline_width: options[:outline_width],
}
flavor[:speed] = options[:speed] if options[:speed] && !options[:speed].empty?

entry = {
  term: options[:term],
  flavor: flavor,
  ts: Time.now.utc.iso8601,
  source: options[:source],
}

cache_file = options[:file] || default_cache_file
begin
  FileUtils.mkdir_p(File.dirname(cache_file))
  File.open(cache_file, "a") { |f| f.puts(JSON.generate(entry)) }
rescue StandardError => e
  # Surface the error and exit non-zero so the caller (selector wrapper)
  # can decide whether to ignore it — never silently drop.
  STDERR.puts "cache-record: failed to append to #{cache_file}: #{e.message}"
  exit 1
end

STDOUT.puts cache_file
