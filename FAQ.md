# Edit Field During Review (Native) - FAQ

## I can't edit the cards while reviewing!

Ensure that you have updated your card templates to use the `edit:` filter. For example, change `{{Front}}` to `{{edit:Front}}`. 

Note that you must **Ctrl + Click** (or **Cmd + Click** on Mac) on the field content to trigger the native editor.

## How do I style the editable fields?

When the Ctrl key is held down, editable fields are highlighted. You can customize this by adding CSS to your note type's Styling section:

```css
/* Styling for fields that can be edited */
[data-efdrc-idx] {
    /* your styles here */
}

/* Styling specifically when Ctrl is held down */
.efdrc-ctrl [data-efdrc-idx] {
    outline: 1px dashed #0078d4;
}
```

## Can I use the editor's shortcuts?

Yes! Since this add-on embeds the native Anki editor, all standard editor shortcuts (like `Ctrl+Shift+C` for clozes or `Ctrl+B` for bold) work exactly as they do in the main editor window.

## How do I close the editor?

You can click the **Done** button at the top of the editor or press **Ctrl + Enter** to save and return to your review.
