from utils import contains_profanity, normalize_text


def test_normalize_text():
    assert normalize_text("ПрИвет, Мир!!!") == "привет мир"
    assert normalize_text("  hello\nworld ") == "hello world"


def test_contains_profanity():
    words = {"spam", "badword"}
    assert contains_profanity("Это spam сообщение", words)
    assert contains_profanity("BADWORD!!!", words)
    assert not contains_profanity("чистый текст", words)
