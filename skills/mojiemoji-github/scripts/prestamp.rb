#!/usr/bin/env ruby

require "optparse"
require "uri"
require "cgi"
require "yaml"
require "zlib"

DEFAULT_BASE_URL = "https://mojiemoji.jozo.beer"
CATALOG_PATH = File.expand_path("../data/prestamp-catalog.yml", __dir__)

catalog_data = YAML.safe_load_file(CATALOG_PATH)

DEFAULT_FLAVOR = catalog_data.fetch("defaults").transform_keys(&:to_sym).freeze
CATALOG = catalog_data.fetch("terms").transform_values { |variants|
  variants.map { |variant| variant.transform_keys(&:to_sym).freeze }.freeze
}.freeze

TERM_RE = Regexp.union(CATALOG.keys.sort_by { |term| [-term.length, term] })

options = {
  base_url: DEFAULT_BASE_URL,
  seed: "0",
}

OptionParser.new do |parser|
  parser.banner = "Usage: prestamp.rb [--seed SEED] [--base-url URL] < input.md > output.md"
  parser.on("--seed SEED", "Seed for deterministic flavor selection") { |v| options[:seed] = v }
  parser.on("--base-url URL", "Base URL for the mojiemoji service") { |v| options[:base_url] = v }
end.parse!

def build_url(base_url, text, flavor)
  params = DEFAULT_FLAVOR.merge(flavor.transform_keys(&:to_sym))
  query = URI.encode_www_form({
    "font" => params[:font],
    "color" => params[:color],
    "animation" => params[:animation],
    "speed" => params[:speed],
    "background" => params[:background],
    "outline" => params[:outline],
    "outline_width" => params[:outline_width],
  }.compact)
  encoded = URI::DEFAULT_PARSER.escape(text)
  "#{base_url}/emoji/#{encoded}?#{query}"
end

def render_img(base_url, text, flavor)
  url = build_url(base_url, text, flavor)
  alt = CGI.escapeHTML(text)
  src = CGI.escapeHTML(url)
  %(<img src="#{src}" alt="#{alt}" height="24" align="absmiddle">)
end

def shields_badge_url?(url)
  url.match?(%r{\Ahttps?://img\.shields\.io(?:/|\z)}i)
end

class Masker
  def initialize
    @tokens = []
  end

  def mask(text)
    token = "__MOJIEMOJI_MASK_#{@tokens.length}__"
    @tokens << text
    token
  end

  def restore(text)
    restored = text
    @tokens.each_with_index.to_a.reverse_each do |original, idx|
      restored = restored.gsub("__MOJIEMOJI_MASK_#{idx}__", original)
    end
    restored
  end
end

def protect_and_replace(text, base_url:, seed:, state:)
  masker = Masker.new
  protected = text.dup

  protected.gsub!(/`[^`\n]*`/) { |m| masker.mask(m) }
  protected.gsub!(/<[^>]+>/) { |m| masker.mask(m) }

  protected.gsub!(/!\[([^\]]*)\]\(([^)]+)\)/) do
    alt = Regexp.last_match(1)
    url = Regexp.last_match(2)
    if shields_badge_url?(url)
      "![#{masker.mask(alt)}](#{masker.mask(url)})"
    else
      "![#{alt}](#{masker.mask(url)})"
    end
  end

  protected.gsub!(/(!?\[[^\]]*\]\()([^)]+)(\))/) do
    target = Regexp.last_match(2)
    if target.start_with?("__MOJIEMOJI_MASK_")
      Regexp.last_match(0)
    else
      "#{Regexp.last_match(1)}#{masker.mask(target)}#{Regexp.last_match(3)}"
    end
  end

  protected.gsub!(%r{https?://[^\s<>)"']+}) { |m| masker.mask(m) }

  protected.gsub!(TERM_RE) do |term|
    variants = CATALOG.fetch(term)
    key = "#{seed}:#{term}:#{state[:occurrence]}"
    state[:occurrence] += 1
    variant = variants[Zlib.crc32(key) % variants.length]
    render_img(base_url, term, variant)
  end

  masker.restore(protected)
end

def transform_line(line, base_url:, seed:, state:)
  output = +""
  cursor = 0

  loop do
    summary_open = /<summary\b[^>]*>/.match(line, cursor)

    if state[:in_summary]
      summary_close = /<\/summary>/.match(line, cursor)
      if summary_close
        output << line[cursor...summary_close.end(0)]
        cursor = summary_close.end(0)
        state[:in_summary] = false
        next
      end
      output << line[cursor..]
      break
    end

    if summary_open
      segment = line[cursor...summary_open.begin(0)]
      output << protect_and_replace(segment, base_url: base_url, seed: seed, state: state)
      output << summary_open[0]
      cursor = summary_open.end(0)
      state[:in_summary] = true
      next
    end

    segment = line[cursor..]
    output << protect_and_replace(segment, base_url: base_url, seed: seed, state: state)
    break
  end

  output
end

input = STDIN.read

in_fence = false
state = { occurrence: 0, in_summary: false }
lines = input.lines
result = lines.map do |line|
  if line =~ /^```/
    in_fence = !in_fence
    line
  elsif in_fence
    line
  else
    transform_line(line, base_url: options[:base_url].sub(%r{/$}, ""), seed: options[:seed], state: state)
  end
end.join

STDOUT.write(result)
