# Edit Field During Review (Native) - FAQ

## I can't edit the cards while reviewing!

By default, all fields are editable during review. You can still use the `edit:` filter for explicit control, but it is optional. If you have disabled auto-enable in the add-on config, update your template fields to use `{{edit:FieldName}}`.

Note that you must **Ctrl + Click** (or **Cmd + Click** on Mac) on the field content to trigger the native editor.

## How do I style the editable fields?

When the Ctrl key is held down, editable fields are highlighted. You can customize this by adding CSS to your note type's Styling section:

```css
/* Styling for fields that can be edited */
[data-efdrc-idx] {
    /* your styles here */
}

/* Styling specifically when the trigger modifier is active */
.efdrc-active [data-efdrc-idx] {
    outline: 1px dashed #0078d4;
}
```

## Can I use the editor's shortcuts?

Yes! Since this add-on embeds the native Anki editor, all standard editor shortcuts (like `Ctrl+Shift+C` for clozes or `Ctrl+B` for bold) work exactly as they do in the main editor window.

## How do I close the editor?

You can click the **Done** button at the top of the editor, press **Ctrl + Enter**, or press **Esc** to save and return to your review.
