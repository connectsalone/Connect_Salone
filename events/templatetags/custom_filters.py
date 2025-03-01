from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Returns the value for the key in the dictionary."""
    return dictionary.get(key)
