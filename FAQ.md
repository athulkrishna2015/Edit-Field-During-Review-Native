# Edit Field During Review (Native) - FAQ

## I can't edit the cards while reviewing!

By default, note fields rendered during review are editable. You can still use the `edit:` filter for explicit control, but it is optional. If you have disabled auto-enable in the add-on config, update your template fields to use `{{edit:FieldName}}`.

On normal cards, use **Ctrl + Click** (or **Cmd + Click** on Mac) on the field content to trigger the native editor.

For **Image Occlusion** cards, you can **Ctrl + Click** the image, use the optional review screen **Edit (N)** button, or press **N** to open the embedded editor. The `Edit (N)` button is off by default and can be enabled in the add-on config.

## How do I style the editable fields?

When the trigger modifier is held down, editable fields and Image Occlusion areas are highlighted. You can customize this by adding CSS to your note type's Styling section:

```css
/* Styling for fields that can be edited */
[data-efdrc-idx],
.image-occlusion,
.canvas-container,
.upper-canvas,
#image {
    /* your styles here */
}

/* Styling specifically when the trigger modifier is active */
.efdrc-active [data-efdrc-idx],
.efdrc-active .image-occlusion,
.efdrc-active .canvas-container,
.efdrc-active .upper-canvas,
.efdrc-active #image {
    outline: 1px dashed #0078d4;
}
```

## Can I use the editor's shortcuts?

Yes. Since this add-on embeds the native Anki editor, standard editor shortcuts like `Ctrl+Shift+C` for clozes or `Ctrl+B` for bold work the same way they do in the main editor window.

## How do I close the editor?

You can click the **Done** button at the top of the editor, press **Ctrl + Enter**, or press **Esc** to save and return to your review.

## How do I undo changes inside the embedded editor?

By default, **Ctrl + Z** uses the embedded editor's normal undo. If you enable **Custom Undo** in the add-on config, **Ctrl + Z** can instead use **Per-Field Revert** or **Full Snapshot Revert**. **Ctrl + Y** continues to work for redo.
