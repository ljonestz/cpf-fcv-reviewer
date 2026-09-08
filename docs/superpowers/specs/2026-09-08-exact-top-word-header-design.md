# Exact top edge Word header design

## Decision

Match the user-edited report with a navy banner that reaches the top and both side
edges of every page. Keep the header text aligned with the one-inch body margin.

## Implementation

Use one ordinary shaded paragraph in Word's default header. Give it negative one-inch
left and right indents, a one-inch first-line indent, zero header distance, white text,
and the existing teal bottom rule. Do not create a separate even-page header. Retain
the existing body margins, footer, report content, and pagination behavior.

## Acceptance

Both Guinea examples must render with the same banner height and placement on every
page. The header must contain no shape, image, table, text box, or anchored object.
If Word cannot render this consistently, revert to the plain non-color header.
