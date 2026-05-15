#!/usr/bin/env ruby

require "optparse"

SURFACE_THRESHOLDS = {
  "issue-body" => { min_density: 2.0, min_sentence_hit: 0.30, min_paragraph_hit: 0.40, max_consecutive_unstamped_paragraphs: 2 },
  "pr-body" => { min_density: 2.0, min_sentence_hit: 0.30, min_paragraph_hit: 0.40, max_consecutive_unstamped_paragraphs: 2 },
  "review-body" => { min_density: 2.5, min_sentence_hit: 0.35, min_paragraph_hit: 0.50, max_consecutive_unstamped_paragraphs: 1 },
  "comment-body" => { min_density: 2.5, min_sentence_hit: 0.35, min_paragraph_hit: 0.50, max_consecutive_unstamped_paragraphs: 1 },
  "release-note" => { min_density: 1.8, min_sentence_hit: 0.25, min_paragraph_hit: 0.40, max_consecutive_unstamped_paragraphs: 2 },
}.freeze

options = {
  surface: "issue-body",
  mode: "warn",
}

OptionParser.new do |parser|
  parser.banner = "Usage: coverage.rb [--surface SURFACE] [--mode warn|block] < input.md"
  parser.on("--surface SURFACE", SURFACE_THRESHOLDS.keys, "Surface type for thresholds") { |v| options[:surface] = v }
  parser.on("--mode MODE", %w[warn block], "warn: stderr only, block: exit 2 on threshold failures") { |v| options[:mode] = v }
end.parse!

text = STDIN.read
threshold = SURFACE_THRESHOLDS.fetch(options[:surface])

stamp_url_re = %r{https?://mojiemoji\.jozo\.beer/emoji/[^\s"')<>]+}
stamp_count = text.scan(stamp_url_re).size
japanese_char_count = text.scan(/[぀-ゟ゠-ヿ一-鿿]/).size

density = japanese_char_count.zero? ? 0.0 : (stamp_count * 100.0 / japanese_char_count)

sentences = text.split(/[。．！？!?\n]+/).map(&:strip).reject(&:empty?)
sentence_hits = sentences.count { |sentence| sentence.include?("mojiemoji.jozo.beer/emoji/") }
sentence_hit_rate = sentences.empty? ? 0.0 : sentence_hits.to_f / sentences.length

paragraphs = text.split(/\n{2,}/).map(&:strip).reject(&:empty?)
paragraph_stamp_counts = paragraphs.map { |paragraph| paragraph.scan(stamp_url_re).size }
paragraph_hits = paragraph_stamp_counts.count { |count| count.positive? }
paragraph_hit_rate = paragraphs.empty? ? 0.0 : paragraph_hits.to_f / paragraphs.length

max_consecutive_unstamped = 0
current_run = 0
paragraph_stamp_counts.each do |count|
  if count.zero?
    current_run += 1
    max_consecutive_unstamped = [max_consecutive_unstamped, current_run].max
  else
    current_run = 0
  end
end

failures = []
failures << format("density %.2f < %.2f (stamps=%d, japanese_chars=%d)", density, threshold[:min_density], stamp_count, japanese_char_count) if density < threshold[:min_density]
failures << format("sentence_hit_rate %.2f < %.2f (%d/%d)", sentence_hit_rate, threshold[:min_sentence_hit], sentence_hits, sentences.length) if sentence_hit_rate < threshold[:min_sentence_hit]
failures << format("paragraph_hit_rate %.2f < %.2f (%d/%d)", paragraph_hit_rate, threshold[:min_paragraph_hit], paragraph_hits, paragraphs.length) if paragraph_hit_rate < threshold[:min_paragraph_hit]
if max_consecutive_unstamped > threshold[:max_consecutive_unstamped_paragraphs]
  failures << format(
    "consecutive_unstamped_paragraphs %d > %d",
    max_consecutive_unstamped,
    threshold[:max_consecutive_unstamped_paragraphs],
  )
end

STDOUT.puts(
  format(
    "surface=%s stamps=%d japanese_chars=%d density=%.2f sentence_hit_rate=%.2f paragraph_hit_rate=%.2f max_consecutive_unstamped=%d",
    options[:surface],
    stamp_count,
    japanese_char_count,
    density,
    sentence_hit_rate,
    paragraph_hit_rate,
    max_consecutive_unstamped,
  ),
)

if failures.any?
  failures.each { |failure| STDERR.puts("coverage warning: #{failure}") }
  exit 2 if options[:mode] == "block"
end
