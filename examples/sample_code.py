"""A deliberately flawed file to try PerenicAI on.

Run:  python -m perenic review examples/sample_code.py
"""


def add_item(item, basket=[]):
    basket.append(item)
    return basket


def load_config(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        return None  # TODO: log the error


def create_user(name, email, age, country, phone, newsletter):
    """Create a user record."""
    return {"name": name, "email": email, "age": age, "country": country, "phone": phone, "newsletter": newsletter}
