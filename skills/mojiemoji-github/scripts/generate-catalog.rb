#!/usr/bin/env ruby
#
# generate-catalog.rb — produce YAML catalog variants for prestamp.rb.
#
# Reads a list of stampable terms (one per line) from --input or stdin and
# emits a `terms:`-shaped YAML fragment to stdout. Variants are picked
# deterministically per term: different font, animation, and color across
# the N variants. Outline hex is BGR-rotated from the fill color. Rotational
# animations (kaiten / kage_kaiten) get speed: slow. Color-shifting
# animations (kira / disco / psycho) get outline_width: "0" to suppress the
# halo. Inline-problematic animations are excluded from the pool.
#
# Terms that exceed the single-stamp length rule (kanji ≤2, katakana ≤3,
# ascii ≤3, hiragana ≤4) are skipped with a stderr notice — those need to
# be split into adjacent stamps and the current prestamp.rb does not do that.
#
# Usage:
#   echo -e "完成\n障害\nDB" | ruby scripts/generate-catalog.rb --seed 42
#   ruby scripts/generate-catalog.rb --input terms.txt --seed 42 --variants 3

require "optparse"
require "digest"

CANONICAL_FONTS = %w[
  akzk chikara dela gothic gothic-bold hachimaru kurobara
  maru maru-bold mincho noto pixel rampart tamanegi toge zero
].freeze

CANONICAL_ANIMATIONS = %w[
  bakusan bane bure chirichiri chuuou_zoom disco ekken gatagata
  kage_bokashi kage_kaiten kage_neon kaiten kira kirari mabataki
  mochimochi mozaiku nami neruneru norinori patapata poyoon psycho
  shuchusen tate_ekken tate_scroll tatemoya tenmetsu yatta
  yoko_scroll yokomoya yurayura zairu zanzo
].freeze

# Tailwind 300-500 dark-mode-safe palette curated from references/parameters.md.
TAILWIND_PALETTE = %w[
  ef4444 dc2626 f97316 ea580c f59e0b d97706
  eab308 ca8a04 22c55e 16a34a 34d399 10b981
  06b6d4 0891b2 3b82f6 2563eb 60a5fa 8b5cf6
  7c3aed a855f7 c084fc d946ef ec4899 db2777
  f472b6 fb7185 f43f5e fdba74
].freeze

COLOR_SHIFTING_ANIMATIONS = %w[kira disco psycho].freeze
ROTATIONAL_ANIMATIONS = %w[kaiten kage_kaiten].freeze

# Inline-problematic animations (per references/parameters.md): block-only or
# obscure letterforms at body height. Excluded from the generated pool.
INLINE_PROBLEMATIC_ANIMATIONS = %w[bakusan chuuou_zoom].freeze

POOLED_ANIMATIONS = (CANONICAL_ANIMATIONS - INLINE_PROBLEMATIC_ANIMATIONS).freeze

def char_classes(term)
  {
    kanji: term.scan(/\p{Han}/).size,
    hira: term.scan(/\p{Hiragana}/).size,
    kata: term.scan(/\p{Katakana}/).size,
    ascii: term.scan(/[A-Za-z0-9]/).size,
  }
end

def fits_single_stamp?(term)
  c = char_classes(term)
  c[:kanji] <= 2 && c[:kata] <= 3 && c[:ascii] <= 3 && c[:hira] <= 4
end

def bgr_rotate(hex)
  raise ArgumentError, "bad hex: #{hex}" unless hex.match?(/\A[0-9a-fA-F]{6}\z/)
  hex[4, 2] + hex[0, 2] + hex[2, 2]
end

def seeded_random(seed, term, axis)
  raw = Digest::SHA256.hexdigest("#{seed}:#{term}:#{axis}")
  Random.new(raw.to_i(16) % (2**32))
end

def generate_variants(term, seed:, count:)
  fonts = CANONICAL_FONTS.shuffle(random: seeded_random(seed, term, "font"))
  animations = POOLED_ANIMATIONS.shuffle(random: seeded_random(seed, term, "anim"))
  colors = TAILWIND_PALETTE.shuffle(random: seeded_random(seed, term, "color"))

  (0...count).map do |i|
    font = fonts[i % fonts.size]
    animation = animations[i % animations.size]
    color = colors[i % colors.size]
    {
      font: font,
      color: color,
      animation: animation,
      outline: COLOR_SHIFTING_ANIMATIONS.include?(animation) ? nil : bgr_rotate(color),
      outline_width: COLOR_SHIFTING_ANIMATIONS.include?(animation) ? "0" : nil,
      speed: ROTATIONAL_ANIMATIONS.include?(animation) ? "slow" : nil,
    }.compact
  end
end

def render_variant(variant, indent)
  lines = []
  lines << "#{indent}- font: #{variant[:font]}"
  lines << "#{indent}  color: \"#{variant[:color]}\""
  lines << "#{indent}  outline: \"#{variant[:outline]}\"" if variant[:outline]
  lines << "#{indent}  outline_width: \"#{variant[:outline_width]}\"" if variant[:outline_width]
  lines << "#{indent}  animation: #{variant[:animation]}"
  lines << "#{indent}  speed: #{variant[:speed]}" if variant[:speed]
  lines.join("\n")
end

options = { seed: "0", variants: 3, input: nil }
OptionParser.new do |parser|
  parser.banner = "Usage: generate-catalog.rb [--seed SEED] [--variants N] [--input FILE] < terms.txt"
  parser.on("--seed SEED", "Seed for deterministic variant selection") { |v| options[:seed] = v }
  parser.on("--variants N", Integer, "Variants per term (default 3)") { |v| options[:variants] = v }
  parser.on("--input FILE", "Read terms from FILE instead of stdin") { |v| options[:input] = v }
end.parse!

source = options[:input] ? File.read(options[:input]) : STDIN.read
terms = source.lines.map(&:strip).reject { |line| line.empty? || line.start_with?("#") }
terms = terms.map { |line| line.split(/\s+/, 2).first }.compact.uniq

terms.each do |term|
  unless fits_single_stamp?(term)
    counts = char_classes(term)
    STDERR.puts(format(
      "skip: %s exceeds length rule (kanji=%d kata=%d ascii=%d hira=%d; max 2/3/3/4)",
      term, counts[:kanji], counts[:kata], counts[:ascii], counts[:hira],
    ))
    next
  end

  STDOUT.puts
  STDOUT.puts "  #{term}:"
  generate_variants(term, seed: options[:seed], count: options[:variants]).each do |variant|
    STDOUT.puts render_variant(variant, "    ")
  end
end
