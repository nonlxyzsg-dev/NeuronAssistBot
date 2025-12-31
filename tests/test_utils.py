from utils import normalize_text, load_profanity_list, build_profanity_pattern
from moderation import ProfanityFilter


def test_normalize_text_basic():
    assert normalize_text("  HeLLo   WoRld  ") == "hello world"


def test_build_profanity_pattern_detects_word(tmp_path):
    word_file = tmp_path / "profanity.txt"
    word_file.write_text("testword\n", encoding="utf-8")
    words = load_profanity_list(str(word_file))
    pattern = build_profanity_pattern(words)
    assert pattern.search("Это TestWord внутри")


def test_profanity_filter_custom_file(tmp_path):
    word_file = tmp_path / "profanity.txt"
    word_file.write_text("spamword\n", encoding="utf-8")
    pf = ProfanityFilter(str(word_file))
    assert pf.is_profane("Сообщение со SpamWord")
    assert not pf.is_profane("Чистый текст без слов")
