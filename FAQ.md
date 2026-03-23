# Edit Field During Review (Native) - FAQ

## I can't edit the cards while reviewing!

By default, all fields are editable during review. You can still use the `edit:` filter for explicit control, but it is optional. If you have disabled auto-enable in the add-on config, update your template fields to use `{{edit:FieldName}}`.

On normal cards, use **Ctrl + Click** (or **Cmd + Click** on Mac) on the field content to trigger the native editor.

For **Image Occlusion** cards, you can **Ctrl + Click** the image, use the review screen's **Edit** button, or press **E** to open the embedded editor.

## How do I style the editable fields?

When the trigger modifier is held down, editable fields and Image Occlusion areas are highlighted. You can customize this by adding CSS to your note type's Styling section:

```css
/* Styling for fields that can be edited */
[data-efdrc-idx], #io-overlay, #io-wrapper {
    /* your styles here */
}

/* Styling specifically when the trigger modifier is active */
.efdrc-active [data-efdrc-idx],
.efdrc-active #io-overlay,
.efdrc-active #io-wrapper {
    outline: 1px dashed #0078d4;
}
```

## Can I use the editor's shortcuts?

Yes. Since this add-on embeds the native Anki editor, standard editor shortcuts like `Ctrl+Shift+C` for clozes or `Ctrl+B` for bold work the same way they do in the main editor window.

## How do I close the editor?

You can click the **Done** button at the top of the editor, press **Ctrl + Enter**, or press **Esc** to save and return to your review.

## How do I undo changes inside the embedded editor?

Use **Ctrl + Z** while the embedded editor is open, or click the **Undo Edit** button beside **Done**. If another add-on or a global shortcut still overrides `Ctrl+Z`, set a dedicated fallback in **Tools > Add-ons > EFDRN > Config > Custom Undo Shortcut**.

## Known Issues

- **Undo/Redo Stability**: We've improved the undo/redo functionality to fix cursor jumping and formatting issues (like bolding), but it may still be inconsistent in very complex editing scenarios. We are continuing to refine the integration with Anki's internal editor history.
