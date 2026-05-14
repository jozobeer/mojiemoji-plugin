#!/usr/bin/env ruby

require "optparse"
require "uri"

options = {
  base_url: "https://mojiemoji.jozo.beer",
  mode: :path,
  format: :markdown,
  background: "transparent",
}

OptionParser.new do |parser|
  parser.banner = "Usage: mojiemoji_markdown.rb --text TEXT [options]"

  parser.on("--text TEXT", "Render text as a mojiemoji image") { |v| options[:text] = v }
  parser.on("--alt TEXT", "Alt text; defaults to --text") { |v| options[:alt] = v }
  parser.on("--base-url URL", "Base URL for the mojiemoji service") { |v| options[:base_url] = v }
  parser.on("--path", "Use /emoji/{text} form (default)") { options[:mode] = :path }
  parser.on("--query", "Use /emoji?q={text} form") { options[:mode] = :query }
  parser.on("--html", "Output HTML img tag instead of markdown") { options[:format] = :html }
  parser.on("--inline", "Shortcut for inline stamps: --html --height 24 --align absmiddle") do
    options[:format] = :html
    options[:height] ||= "24"
    options[:align] ||= "absmiddle"
  end
  parser.on("--height VALUE", "img height attribute (html only)") { |v| options[:height] = v }
  parser.on("--width VALUE", "img width attribute (html only)") { |v| options[:width] = v }
  parser.on("--align VALUE", "img align attribute, e.g. absmiddle (html only)") { |v| options[:align] = v }
  parser.on("--font VALUE", "font parameter") { |v| options[:font] = v }
  parser.on("--color VALUE", "color parameter") { |v| options[:color] = v }
  parser.on("--animation VALUE", "animation parameter") { |v| options[:animation] = v }
  parser.on("--speed VALUE", "speed parameter") { |v| options[:speed] = v }
  parser.on("--gradient VALUE", "gradient parameter") { |v| options[:gradient] = v }
  parser.on("--flip VALUE", "flip parameter") { |v| options[:flip] = v }
  parser.on("--padding VALUE", "padding parameter") { |v| options[:padding] = v }
  parser.on("--background VALUE", "background parameter (default: transparent)") { |v| options[:background] = v }
  parser.on("--outline VALUE", "outline color (hex, 'darker' / 'lighter', or 'triadic' / 'complement' to derive from --color)") { |v| options[:outline] = v }
  parser.on("--outline-width VALUE", "outline width 0..4 px (default 0 = no outline)") { |v| options[:outline_width] = v }
end.parse!

abort "error: --text is required" if options[:text].to_s.empty?

# Animations that cycle through colors (rainbow / strobe). A fixed-color
# outline fights the rainbow effect and looks dirty. When the user picks
# one of these, drop the outline + outline_width params automatically.
COLOR_SHIFTING_ANIMATIONS = %w[disco psycho kira].freeze

def hex_to_hsl(hex)
  h = hex.to_s.delete_prefix("#")
  r, g, b = [h[0..1], h[2..3], h[4..5]].map { |c| c.to_i(16) / 255.0 }
  max = [r, g, b].max
  min = [r, g, b].min
  l = (max + min) / 2.0
  if max == min
    return [0.0, 0.0, l]
  end
  d = max - min
  s = l > 0.5 ? d / (2.0 - max - min) : d / (max + min)
  hue =
    case max
    when r then (g - b) / d + (g < b ? 6 : 0)
    when g then (b - r) / d + 2
    else        (r - g) / d + 4
    end
  [hue * 60.0 % 360.0, s, l]
end

def hsl_to_hex(h, s, l)
  h_frac = (h % 360) / 360.0
  hue_to_rgb = lambda do |p, q, t|
    t += 1 if t < 0
    t -= 1 if t > 1
    return p + (q - p) * 6 * t if t < 1.0 / 6
    return q if t < 1.0 / 2
    return p + (q - p) * (2.0 / 3 - t) * 6 if t < 2.0 / 3
    p
  end
  if s.zero?
    r = g = b = l
  else
    q = l < 0.5 ? l * (1 + s) : l + s - l * s
    p = 2 * l - q
    r = hue_to_rgb.call(p, q, h_frac + 1.0 / 3)
    g = hue_to_rgb.call(p, q, h_frac)
    b = hue_to_rgb.call(p, q, h_frac - 1.0 / 3)
  end
  format("%02x%02x%02x", (r * 255).round, (g * 255).round, (b * 255).round)
end

def hue_rotated(color_hex, degrees)
  return nil unless color_hex&.match?(/\A#?[0-9a-fA-F]{6}\z/)
  h, s, l = hex_to_hsl(color_hex)
  hsl_to_hex(h + degrees, s, l)
end

# Resolve --outline = "triadic" / "complement" into a concrete hex
# derived from --color. The mojiemoji service accepts arbitrary hex
# in the outline param, so we pre-compute and pass the result.
case options[:outline]
when "triadic"
  derived = hue_rotated(options[:color], 120.0)
  options[:outline] = derived || options[:outline]
when "complement"
  derived = hue_rotated(options[:color], 180.0)
  options[:outline] = derived || options[:outline]
end

# Color-shifting animations look messy with a fixed-color outline.
# Drop outline + outline_width so the rainbow effect renders cleanly.
animation_val = options[:animation].to_s.downcase
if COLOR_SHIFTING_ANIMATIONS.include?(animation_val)
  options.delete(:outline)
  options.delete(:outline_width)
end

params = {
  "font" => options[:font],
  "color" => options[:color],
  "animation" => options[:animation],
  "speed" => options[:speed],
  "gradient" => options[:gradient],
  "flip" => options[:flip],
  "padding" => options[:padding],
  "background" => options[:background],
  "outline" => options[:outline],
  "outline_width" => options[:outline_width],
}.compact

base = options[:base_url].sub(%r{/\z}, "")
alt = options[:alt] || options[:text]
path =
  if options[:mode] == :query
    query = URI.encode_www_form({ "q" => options[:text] }.merge(params))
    "/emoji?#{query}"
  else
    suffix = params.empty? ? "" : "?#{URI.encode_www_form(params)}"
    "/emoji/#{URI::DEFAULT_PARSER.escape(options[:text])}#{suffix}"
  end

url = "#{base}#{path}"

def escape_attr(value)
  value.to_s.gsub("&", "&amp;").gsub('"', "&quot;").gsub("<", "&lt;").gsub(">", "&gt;")
end

# Markdown image alt has its own escaping rules. The CommonMark spec treats
# `]` as the alt terminator, `\` as an escape, and a literal newline breaks
# the image syntax altogether. Escape these in the alt before splicing.
def escape_md_alt(value)
  value.to_s
       .gsub("\\", "\\\\\\\\")  # \  →  \\
       .gsub("[", "\\[")
       .gsub("]", "\\]")
       .gsub(/\r?\n/, " ")
end

# Markdown link/image URL is delimited by parentheses. A literal ')' in the
# URL closes it. The mojiemoji service shouldn't return one, but be defensive
# in case of future schema changes.
def escape_md_url(value)
  value.to_s.gsub(")", "%29").gsub("(", "%28")
end

if options[:format] == :html
  attrs = { "src" => url, "alt" => alt }
  attrs["height"] = options[:height] if options[:height]
  attrs["width"] = options[:width] if options[:width]
  attrs["align"] = options[:align] if options[:align]
  rendered = attrs.map { |k, v| %(#{k}="#{escape_attr(v)}") }.join(" ")
  puts "<img #{rendered}>"
else
  puts "![#{escape_md_alt(alt)}](#{escape_md_url(url)})"
end
