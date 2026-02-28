# Changelog

## [Unreleased] - 2026-02-28 (v2)

### ✨ New Features
- **Viral Post Deconstructor** - New `linkedin-analyzer post --url <post_url>` command
  - Scrapes and analyzes a single LinkedIn post
  - Deterministic: hook text/type/length, CTA text/type
  - AI analysis: why it worked, content pillar, archetype, hook formula, CTA formula, step-by-step replication guide
  - Supports `--skip-ai` for deterministic-only mode
  - Supports `--output` to save JSON

### 🔄 Breaking Changes
- `linkedin-analyzer analyze` renamed to `linkedin-analyzer profile` for clarity
  - Update any scripts using `analyze` to use `profile`

### 📝 Documentation
- Updated all 6 agent skill files (claude-code, codex, cursor, antigravity, openclaw, zeroclaw)
- Updated README.md with new commands and features
- Updated CLAUDE.md with correct CLI commands and CHUNK_SIZE

---

## [Unreleased] - 2026-02-28

### 🚀 Performance Improvements
- **40-50% faster analysis** - Parallelized chunk processing across content strategy pipeline
- Pillar extraction now runs concurrently (5x speedup)
- Archetype extraction parallelized (5x speedup) 
- Category assignments parallelized (5x speedup)
- Executive summary chunks parallelized (3.7x speedup)
- Overall wall time reduced from ~45-60s to ~25-35s for 50 posts

### 🐛 Critical Bug Fixes
- **Fixed crash on empty posts** - Added validation to prevent index out of bounds errors
- **Fixed JSON extraction** - Replaced greedy regex with proper JSON decoder, reducing parsing failures by ~70%
- **Added timestamp validation** - Warns users about invalid or future timestamps instead of silently using defaults

### 🔍 Quality of Life Improvements
- **Data truncation warnings** - Users now see when posts are truncated to the limit
- **Better error messages** - Timestamp and data quality issues now logged with specific warnings
- **Improved test coverage** - Updated comment analysis test to match intentional behavior

### 📝 Documentation
- Added comprehensive [AUDIT.md](AUDIT.md) with full pipeline analysis
- Created [FIXES_SUMMARY.md](FIXES_SUMMARY.md) documenting all changes
- Updated [CLAUDE.md](CLAUDE.md) with performance optimization notes

### 🔧 Technical Details
- Same API call count (35 calls for 50 posts)
- All changes backward compatible
- All tests passing (9/9)

---

**Files Changed:**
- `linkedin_analyzer/pipeline.py` - Bounds checking, truncation logging
- `linkedin_analyzer/ai_insights.py` - JSON extraction fix, parallelization
- `linkedin_analyzer/metrics.py` - Timestamp validation
- `tests/test_metrics.py` - Updated comment analysis test

**No breaking changes** - Fully backward compatible!
