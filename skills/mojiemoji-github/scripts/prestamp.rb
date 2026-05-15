#!/usr/bin/env ruby

require "optparse"
require "uri"
require "cgi"
require "zlib"

DEFAULT_BASE_URL = "https://mojiemoji.jozo.beer"

CATALOG = {
  "修正版" => [
    { font: "gothic-bold", color: "3b82f6", animation: "bane", outline: "darker", outline_width: "2" },
    { font: "maru-bold", color: "22c55e", animation: "mochimochi", outline: "darker", outline_width: "2" },
    { font: "noto", color: "8b5cf6", animation: "neruneru", outline: "darker", outline_width: "2" },
  ],
  "修正" => [
    { font: "gothic-bold", color: "ef4444", animation: "gatagata", outline: "darker", outline_width: "2" },
    { font: "akzk", color: "f97316", animation: "ekken", outline: "darker", outline_width: "2" },
    { font: "kurobara", color: "ec4899", animation: "zanzo", outline: "darker", outline_width: "2" },
  ],
  "緊急" => [
    { font: "dela", color: "ef4444", animation: "tenmetsu", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "f59e0b", animation: "shuchusen", outline: "darker", outline_width: "2" },
    { font: "chikara", color: "dc2626", animation: "bure", outline: "darker", outline_width: "2" },
  ],
  "完了" => [
    { font: "pixel", color: "22c55e", animation: "yatta", outline: "darker", outline_width: "2" },
    { font: "maru-bold", color: "34d399", animation: "kirari", outline: "darker", outline_width: "2" },
    { font: "zero", color: "10b981", animation: "nami", outline: "darker", outline_width: "2" },
  ],
  "失敗" => [
    { font: "mincho", color: "dc2626", animation: "bure", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "ef4444", animation: "gatagata", outline: "darker", outline_width: "2" },
    { font: "akzk", color: "f97316", animation: "ekken", outline: "darker", outline_width: "2" },
  ],
  "成功" => [
    { font: "maru-bold", color: "34d399", animation: "kira", background: "transparent" },
    { font: "gothic-bold", color: "22c55e", animation: "kirari", outline: "darker", outline_width: "2" },
    { font: "noto", color: "60a5fa", animation: "yatta", outline: "darker", outline_width: "2" },
  ],
  "重要" => [
    { font: "mincho", color: "f59e0b", animation: "shuchusen", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "f97316", animation: "ekken", outline: "darker", outline_width: "2" },
    { font: "dela", color: "ef4444", animation: "tenmetsu", outline: "darker", outline_width: "2" },
  ],
  "注意" => [
    { font: "gothic-bold", color: "f97316", animation: "mabataki", outline: "darker", outline_width: "2" },
    { font: "mincho", color: "ea580c", animation: "tenmetsu", outline: "darker", outline_width: "2" },
    { font: "akzk", color: "f59e0b", animation: "chirichiri", outline: "darker", outline_width: "2" },
  ],
  "対応" => [
    { font: "maru-bold", color: "3b82f6", animation: "norinori", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "60a5fa", animation: "nami", outline: "darker", outline_width: "2" },
    { font: "noto", color: "8b5cf6", animation: "patapata", outline: "darker", outline_width: "2" },
  ],
  "確認" => [
    { font: "gothic-bold", color: "60a5fa", animation: "tate_scroll", outline: "darker", outline_width: "2" },
    { font: "maru-bold", color: "3b82f6", animation: "bane", outline: "darker", outline_width: "2" },
    { font: "noto", color: "22c55e", animation: "mabataki", outline: "darker", outline_width: "2" },
  ],
  "歓迎" => [
    { font: "maru", color: "10b981", animation: "poyoon", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "22c55e", animation: "kirari", outline: "darker", outline_width: "2" },
    { font: "noto", color: "34d399", animation: "mochimochi", outline: "darker", outline_width: "2" },
  ],
  "警告" => [
    { font: "mincho", color: "c2410c", animation: "tenmetsu", outline: "darker", outline_width: "2" },
    { font: "dela", color: "dc2626", animation: "ekken", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "f97316", animation: "shuchusen", outline: "darker", outline_width: "2" },
  ],
  "必須" => [
    { font: "akzk", color: "ef4444", animation: "ekken", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "dc2626", animation: "tenmetsu", outline: "darker", outline_width: "2" },
    { font: "dela", color: "f97316", animation: "chirichiri", outline: "darker", outline_width: "2" },
  ],
  "任意" => [
    { font: "noto", color: "8b5cf6", animation: "nami", outline: "darker", outline_width: "2" },
    { font: "maru-bold", color: "a855f7", animation: "poyoon", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "c084fc", animation: "yurayura", outline: "darker", outline_width: "2" },
  ],
  "導入" => [
    { font: "kurobara", color: "22c55e", animation: "kaiten", speed: "slow", outline: "darker", outline_width: "2" },
    { font: "maru-bold", color: "10b981", animation: "norinori", outline: "darker", outline_width: "2" },
    { font: "noto", color: "34d399", animation: "nami", outline: "darker", outline_width: "2" },
  ],
  "削除" => [
    { font: "toge", color: "dc2626", animation: "zanzo", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "ef4444", animation: "bure", outline: "darker", outline_width: "2" },
    { font: "dela", color: "f97316", animation: "ekken", outline: "darker", outline_width: "2" },
  ],
  "追加" => [
    { font: "zero", color: "3b82f6", animation: "patapata", outline: "darker", outline_width: "2" },
    { font: "maru-bold", color: "60a5fa", animation: "bane", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "22c55e", animation: "yatta", outline: "darker", outline_width: "2" },
  ],
  "更新" => [
    { font: "chikara", color: "f59e0b", animation: "chirichiri", outline: "darker", outline_width: "2" },
    { font: "gothic-bold", color: "f97316", animation: "gatagata", outline: "darker", outline_width: "2" },
    { font: "noto", color: "60a5fa", animation: "yurayura", outline: "darker", outline_width: "2" },
  ],
  "PR" => [
    { font: "gothic-bold", color: "3b82f6", animation: "norinori", outline: "darker", outline_width: "2" },
    { font: "maru-bold", color: "8b5cf6", animation: "nami", outline: "darker", outline_width: "2" },
    { font: "noto", color: "ec4899", animation: "mozaiku", outline: "darker", outline_width: "2" },
  ],
}.freeze

DEFAULT_FLAVOR = {
  background: "transparent",
  outline: "darker",
  outline_width: "2",
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
    if url.include?("img.shields.io")
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
