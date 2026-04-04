def word_count(text):
    """Count occurrences of words in text."""
    words = text.split()
    counts = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    return counts