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

# Per-character class detection for split_term. `:other` is reserved for
# punctuation, symbols, and characters outside the four scripts we track
# (Han / Hiragana / Katakana / ASCII alphanumerics) — full-width katakana
# extensions such as ヴ match \p{Katakana} and ASCII digits 0-9 match the
# /[A-Za-z0-9]/ branch, so neither falls through to `:other`.
def char_class_of(c)
  case c
  when /\p{Han}/ then :kanji
  when /\p{Hiragana}/ then :hira
  when /\p{Katakana}/ then :kata
  when /[A-Za-z0-9]/ then :ascii
  else :other
  end
end

# Common 1-char kanji prefixes that modify a 2-kanji core (negation /
# scope / re- / mis-). When the term is exactly 3 kanji and starts
# with one of these, split as `[prefix, 2-kanji core]` — semantically
# correct for most 3-kanji compounds in technical Japanese.
#
# Suffix nominalizers (度 / 性 / 化 etc.) take priority when both match
# the same term (e.g., `不明点` has both 不 prefix and 点 suffix; the
# suffix split `不明 + 点` reads better).
KANJI_PREFIX_MODIFIERS = %w[
  不 未 誤 再 副 要 非 初 永 拡 超 最 前 後 旧 新 全 半 各 同 異 逆 反 主 準
].freeze

KANJI_SUFFIX_NOMINALIZERS = %w[
  度 性 化 像 点 感 観 論 様 力 法 体 系 軸 値
].freeze

# Split a term into 2 adjacent-stamp chunks when it exceeds the
# single-stamp length rule. Returns [left, right] or nil if no valid
# split exists. Priority per SKILL.md § "境界ヒューリスティック":
#
#   1. Character-class boundary (katakana ↔ kanji ↔ hiragana)
#   2. Pure-kanji morpheme heuristic (suffix > prefix > 2+1 fallback)
#   3. Pure-katakana 3+remainder split
def split_term(term)
  chars = term.chars
  return nil if chars.length < 2

  classes = chars.map { |c| char_class_of(c) }

  # 1. Character-class boundary. Walk through every class transition
  # and return the first one where both sides fit a single stamp.
  # This handles mixed-script terms like `マージ歓迎` (katakana ↔
  # kanji), `修正お願い` (kanji ↔ hiragana), `引き続き` (kanji ↔ hira
  # ↔ kanji ↔ hira — splits at the first valid balanced boundary).
  (1...chars.length).each do |idx|
    next if classes[idx] == classes[idx - 1]
    left = chars[0...idx].join
    right = chars[idx..].join
    return [left, right] if fits_single_stamp?(left) && fits_single_stamp?(right)
  end

  # 2. Pure-kanji words.
  if classes.uniq == [:kanji]
    if chars.length == 3
      # Suffix nominalizer wins ties — `不明点` → `不明 + 点` (suffix
      # 点) over `不 + 明点` (prefix 不), because `不明` is a real
      # word and `明点` isn't.
      return [chars[0..-2].join, chars[-1]] if KANJI_SUFFIX_NOMINALIZERS.include?(chars[-1])
      return [chars[0], chars[1..].join] if KANJI_PREFIX_MODIFIERS.include?(chars[0])
      return [chars[0..1].join, chars[2..].join]
    elsif chars.length == 4
      return [chars[0..1].join, chars[2..].join]
    end
  end

  # 3. Pure katakana ≥4: prefer 3+remainder, fall back to 2+remainder.
  if classes.uniq == [:kata] && chars.length >= 4
    [3, 2].each do |split_at|
      left = chars[0...split_at].join
      right = chars[split_at..].join
      return [left, right] if fits_single_stamp?(left) && fits_single_stamp?(right)
    end
  end

  nil
end

def bgr_rotate(hex)
  raise ArgumentError, "bad hex: #{hex}" unless hex.match?(/\A[0-9a-fA-F]{6}\z/)
  hex[4, 2] + hex[0, 2] + hex[2, 2]
end

def seeded_random(seed, term, axis)
  raw = Digest::SHA256.hexdigest("#{seed}:#{term}:#{axis}")
  Random.new(raw.to_i(16) % (2**32))
end

# Pre-shuffle the canonical pools once per term, then index into them for
# each variant. Shuffling inside the per-variant loop would be O(variants *
# pool_size) instead of O(pool_size + variants), wasteful for large
# `--variants` counts.
def shuffled_pools(term, seed:)
  {
    fonts: CANONICAL_FONTS.shuffle(random: seeded_random(seed, term, "font")),
    animations: POOLED_ANIMATIONS.shuffle(random: seeded_random(seed, term, "anim")),
    colors: TAILWIND_PALETTE.shuffle(random: seeded_random(seed, term, "color")),
  }
end

def flavor_at(pools, index)
  font = pools[:fonts][index % pools[:fonts].size]
  animation = pools[:animations][index % pools[:animations].size]
  color = pools[:colors][index % pools[:colors].size]
  {
    font: font,
    color: color,
    animation: animation,
    outline: COLOR_SHIFTING_ANIMATIONS.include?(animation) ? nil : bgr_rotate(color),
    outline_width: COLOR_SHIFTING_ANIMATIONS.include?(animation) ? "0" : nil,
    speed: ROTATIONAL_ANIMATIONS.include?(animation) ? "slow" : nil,
  }.compact
end

def generate_variants(term, seed:, count:)
  pools = shuffled_pools(term, seed: seed)
  (0...count).map { |i| flavor_at(pools, i) }
end

# Compound variants: each variant is one shared flavor split across the
# adjacent chunks. SKILL.md prescribes matching font/color/animation across
# the two halves so the split reads as a single cohesive word.
def generate_compound_variants(term, chunks, seed:, count:)
  pools = shuffled_pools(term, seed: seed)
  (0...count).map do |i|
    flavor = flavor_at(pools, i)
    { chunks: chunks.map { |chunk_text| flavor.merge(text: chunk_text) } }
  end
end

# YAML scalars that look numeric (`1`, `42`) parse as Integer keys when bare,
# breaking downstream code that expects String keys (e.g. prestamp.rb's
# `Regexp.union(CATALOG.keys)`). Quote any term whose name is purely digits.
def yaml_safe_key(term)
  term.match?(/\A\d+\z/) ? "\"#{term}\"" : term
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

def render_compound_variant(variant, indent)
  lines = ["#{indent}- chunks:"]
  variant[:chunks].each do |chunk|
    lines << "#{indent}    - text: #{chunk[:text]}"
    lines << "#{indent}      font: #{chunk[:font]}"
    lines << "#{indent}      color: \"#{chunk[:color]}\""
    lines << "#{indent}      outline: \"#{chunk[:outline]}\"" if chunk[:outline]
    lines << "#{indent}      outline_width: \"#{chunk[:outline_width]}\"" if chunk[:outline_width]
    lines << "#{indent}      animation: #{chunk[:animation]}"
    lines << "#{indent}      speed: #{chunk[:speed]}" if chunk[:speed]
  end
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
  if fits_single_stamp?(term)
    STDOUT.puts
    STDOUT.puts "  #{yaml_safe_key(term)}:"
    generate_variants(term, seed: options[:seed], count: options[:variants]).each do |variant|
      STDOUT.puts render_variant(variant, "    ")
    end
  elsif (split = split_term(term))
    STDOUT.puts
    STDOUT.puts "  #{yaml_safe_key(term)}:"
    generate_compound_variants(term, split, seed: options[:seed], count: options[:variants]).each do |variant|
      STDOUT.puts render_compound_variant(variant, "    ")
    end
  else
    counts = char_classes(term)
    STDERR.puts(format(
      "skip: %s — no valid split (kanji=%d kata=%d ascii=%d hira=%d)",
      term, counts[:kanji], counts[:kata], counts[:ascii], counts[:hira],
    ))
  end
end
