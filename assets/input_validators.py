import re
from rest_framework.exceptions import ValidationError

MAX_TAG_LENGTH = 30
MAX_CATEGORY_LENGTH = 50
MAX_TAGS = 10


def validate_text_input(value, field_name, max_length, required=False):
    if not isinstance(value, str):
        raise ValidationError({
            field_name: f"Please enter a valid {field_name}."
        })

    cleaned = value.strip()

    if required and not cleaned:
        raise ValidationError({
            field_name: f"Please enter a {field_name}."
        })

    if len(cleaned) > max_length:
        raise ValidationError({
            field_name: f"{field_name.capitalize()} must not exceed {max_length} characters."
        })

    # Reject control characters, except line breaks and tabs.
    if any(
        ord(char) < 32 and char not in "\n\r\t"
        for char in cleaned
    ):
        raise ValidationError({
            field_name: f"{field_name.capitalize()} contains invalid characters."
        })

    return cleaned


def validate_tag_name(value):
    name = validate_text_input(
        value,
        "tag",
        MAX_TAG_LENGTH,
        required=True
    )

    if not re.fullmatch(r"[\w -]+", name, flags=re.UNICODE):
        raise ValidationError({
            "tags": "Tag contains invalid characters. Please use letters, "
                    "numbers, spaces, underscores or hyphens."
        })

    return name


def validate_category_name(value):
    name = validate_text_input(
        value,
        "category name",
        MAX_CATEGORY_LENGTH,
        required=True
    )

    if not re.fullmatch(r"[\w &-]+", name, flags=re.UNICODE):
        raise ValidationError({
            "name": "Category name contains invalid characters. "
                    "Please use letters, numbers, spaces, "
                    "underscores, hyphens or &."
        })

    return name


def validate_tags_input(raw_tags):
    if raw_tags is None or raw_tags == "":
        return []

    if isinstance(raw_tags, str):
        items = raw_tags.split(",")

    elif isinstance(raw_tags, (list, tuple)):
        items = []

        for value in raw_tags:
            if not isinstance(value, str):
                raise ValidationError({
                    "tags": "Please enter valid tags."
                })

            items.extend(value.split(","))

    else:
        raise ValidationError({
            "tags": "Please enter valid tags."
        })

    if any(not item.strip() for item in items):
        raise ValidationError({
            "tags": "Please remove empty tags."
        })

    if len(items) > MAX_TAGS:
        raise ValidationError({
            "tags": "You can add up to 10 tags only."
        })

    names = [validate_tag_name(item) for item in items]

    if len({name.casefold() for name in names}) != len(names):
        raise ValidationError({
            "tags": "Duplicate tags are not allowed."
        })

    return names
