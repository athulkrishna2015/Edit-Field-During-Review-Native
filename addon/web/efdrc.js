(function() {
    window.EFDRC = {
        config: {
            modifier: 'Ctrl',
            action: 'Click',
            mode: 'reviewer'
        },
        cloneBottomBarButton: function(button) {
            const clonedButton = button.cloneNode(true);
            clonedButton.title = 'Shortcut key: N';

            if (clonedButton.tagName === 'INPUT') {
                clonedButton.value = 'Edit (N)';
            } else {
                clonedButton.textContent = 'Edit (N)';
            }

            return clonedButton;
        },
        injectNativeButton: function() {
            const editBtn = document.querySelector("button[onclick*=\"pycmd('edit')\"], input[onclick*=\"pycmd('edit')\"]");
            const editCell = editBtn ? editBtn.closest('td') : null;
            const middle = document.getElementById('middle');
            if (!editBtn || !editCell || !middle || document.getElementById('efdrc-native-edit-cell')) {
                return;
            }

            const nativeBtn = this.cloneBottomBarButton(editBtn);
            nativeBtn.id = 'efdrc-native-edit';
            nativeBtn.style.marginLeft = '0';
            nativeBtn.onclick = (event) => {
                window.pycmd('EFDRC!edit_native');
                event.preventDefault();
                event.stopPropagation();
            };

            const editGroup = document.createElement('div');
            editGroup.id = 'efdrc-native-edit-cell';
            editGroup.style.display = 'inline-flex';
            editGroup.style.alignItems = 'flex-start';
            editGroup.style.whiteSpace = 'nowrap';
            editGroup.appendChild(editBtn);
            editGroup.appendChild(nativeBtn);
            editCell.replaceChildren(editGroup);

            const placeholderCell = document.createElement('td');
            placeholderCell.id = 'efdrc-native-edit-spacer';
            placeholderCell.className = 'stat';
            placeholderCell.align = 'center';
            placeholderCell.vAlign = 'top';
            placeholderCell.setAttribute('aria-hidden', 'true');

            const placeholderBtn = this.cloneBottomBarButton(editBtn);
            placeholderBtn.tabIndex = -1;
            placeholderBtn.disabled = true;
            placeholderBtn.style.marginLeft = '0';
            placeholderBtn.style.visibility = 'hidden';
            placeholderBtn.style.pointerEvents = 'none';
            placeholderCell.appendChild(placeholderBtn);

            middle.insertAdjacentElement('afterend', placeholderCell);
        },
        setup: function(conf) {
            if (conf) {
                this.config = Object.assign({}, this.config, conf);
            }

            if (this.config.mode === 'bottom') {
                this.injectNativeButton();
                return;
            }

            const handleTrigger = (event) => {
                const modifierMap = {
                    'Ctrl': event.ctrlKey || event.metaKey,
                    'Shift': event.shiftKey,
                    'Alt': event.altKey,
                    'None': true
                };
                
                if (modifierMap[this.config.modifier]) {
                    let el = event.target;
                    while (el && el !== document.body) {
                        if (el.hasAttribute('data-efdrc-idx')) {
                            const idx = el.getAttribute('data-efdrc-idx');
                            window.pycmd('EFDRC!edit#' + idx);
                            event.preventDefault();
                            event.stopPropagation();
                            return;
                        }
                        // Support for Image Occlusion elements
                        if (el.id === 'io-overlay' || el.id === 'io-wrapper' || el.id === 'io-header' || el.id === 'io-footer' || el.id === 'io-image') {
                            window.pycmd('edit');
                            event.preventDefault();
                            event.stopPropagation();
                            return;
                        }
                        el = el.parentElement;
                    }
                }
            };

            const eventType = this.config.action === 'DoubleClick' ? 'dblclick' : 'click';
            document.addEventListener(eventType, handleTrigger, true);

            const updateActiveState = (e, isDown) => {
                const keys = {
                    'Ctrl': ['Control', 'Meta'],
                    'Shift': ['Shift'],
                    'Alt': ['Alt']
                };
                if (this.config.modifier === 'None') {
                    document.body.classList.add('efdrc-active');
                } else if ((keys[this.config.modifier] || []).includes(e.key)) {
                    if (isDown) document.body.classList.add('efdrc-active');
                    else document.body.classList.remove('efdrc-active');
                }
            };

            window.addEventListener('keydown', (e) => updateActiveState(e, true));
            window.addEventListener('keyup', (e) => updateActiveState(e, false));
            window.addEventListener('blur', () => document.body.classList.remove('efdrc-active'));
            
            if (this.config.modifier === 'None') document.body.classList.add('efdrc-active');
        }
    };
})();
