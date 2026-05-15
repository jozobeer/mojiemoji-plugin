#!/usr/bin/env ruby
#
# cache-stats.rb — read the usage JSONL cache and emit promotion candidates
# as a YAML fragment compatible with prestamp-catalog.yml's `terms:` block.
#
# A "candidate" is a unique (term, flavor) pair whose occurrence count is
# at least --threshold across the cache. Identical flavor entries (same
# font/color/animation/outline) are deduplicated so a single term that
# was rendered 5× with one flavor still emits one variant.
#
# Output: empty when no candidates pass the threshold. Otherwise, one
# block per term:
#
#   <term>:
#     - font: <font>
#       color: "<hex>"
#       outline: "<hex|directive>"
#       outline_width: "2"
#       animation: <animation>
#       [speed: <speed>]
#
# Malformed JSONL lines are skipped with a stderr notice; the rest of the
# file is still processed.
#
# Usage:
#   ruby cache-stats.rb --file /path/to/usage.jsonl --threshold 2

require "optparse"
require "json"

def default_cache_file
  env_override = ENV["MOJIEMOJI_CACHE_FILE"]
  return env_override unless env_override.nil? || env_override.empty?

  data_home = ENV["XDG_DATA_HOME"]
  data_home = File.join(Dir.home, ".local", "share") if data_home.nil? || data_home.empty?
  File.join(data_home, "mojiemoji-plugin", "usage.jsonl")
end

options = { threshold: 2 }
parser = OptionParser.new do |opts|
  opts.banner = "Usage: cache-stats.rb [--file PATH] [--threshold N]"
  opts.on("--file PATH", "JSONL cache file (default: $MOJIEMOJI_CACHE_FILE or XDG default)") { |v| options[:file] = v }
  opts.on("--threshold N", Integer, "Minimum occurrence per (term, flavor) (default 2)") { |v| options[:threshold] = v }
end
parser.parse!

cache_file = options[:file] || default_cache_file
exit 0 unless File.exist?(cache_file)

# (term, flavor_fingerprint) => { flavor: Hash, count: Int }
counts = {}
skipped = 0

File.foreach(cache_file) do |raw|
  line = raw.strip
  next if line.empty?
  begin
    entry = JSON.parse(line)
  rescue JSON::ParserError
    # Intentional: count malformed lines so we can report a summary on
    # stderr, then continue processing the rest of the file.
    skipped += 1
    next
  end
  term = entry["term"]
  flavor = entry["flavor"]
  next unless term.is_a?(String) && flavor.is_a?(Hash)

  fingerprint = [
    flavor["font"], flavor["color"], flavor["animation"],
    flavor["outline"], flavor["outline_width"], flavor["speed"],
  ]
  key = [term, fingerprint]
  bucket = counts[key] ||= { flavor: flavor, count: 0 }
  bucket[:count] += 1
end

STDERR.puts "cache-stats: skipped #{skipped} malformed line(s)" if skipped > 0

candidates_by_term = Hash.new { |h, k| h[k] = [] }
counts.each do |(term, _fingerprint), bucket|
  next if bucket[:count] < options[:threshold]
  candidates_by_term[term] << bucket[:flavor]
end

exit 0 if candidates_by_term.empty?

def yaml_value(value)
  return value if value.is_a?(Integer)
  s = value.to_s
  return s if s.match?(/\A[a-z][a-z0-9_]*\z/i) && !s.match?(/\A\d/) && !s.match?(/\A[0-9a-f]{6}\z/)
  "\"#{s}\""
end

# Term keys may contain YAML-significant characters (`:`, `>`, `#`, ` -`,
# leading symbols, etc.). Always quote to keep the emitted fragment a
# valid YAML mapping. JSON-style double-quoted scalars handle the common
# cases; embedded `"` and `\` get escaped.
def yaml_term_key(term)
  escaped = term.to_s.gsub("\\", "\\\\").gsub("\"", "\\\"")
  "\"#{escaped}\""
end

candidates_by_term.sort.each do |term, variants|
  STDOUT.puts "  #{yaml_term_key(term)}:"
  variants.each do |flavor|
    STDOUT.puts "    - font: #{flavor['font']}"
    STDOUT.puts "      color: #{yaml_value(flavor['color'])}"
    STDOUT.puts "      outline: #{yaml_value(flavor['outline'])}" if flavor['outline']
    if flavor['outline_width']
      STDOUT.puts "      outline_width: #{yaml_value(flavor['outline_width'])}"
    end
    STDOUT.puts "      animation: #{flavor['animation']}"
    STDOUT.puts "      speed: #{flavor['speed']}" if flavor['speed']
  end
end
