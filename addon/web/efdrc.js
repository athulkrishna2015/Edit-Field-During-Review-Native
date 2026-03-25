(function() {
    window.EFDRC = {
        config: {
            modifier: 'Ctrl',
            action: 'Click',
            mode: 'reviewer'
        },
        injectNativeButton: function() {
            const editBtn = document.querySelector("button[onclick*=\"pycmd('edit')\"], input[onclick*=\"pycmd('edit')\"]");
            if (!editBtn || document.getElementById('efdrc-native-edit')) {
                return;
            }

            const nativeBtn = editBtn.cloneNode(true);
            nativeBtn.id = 'efdrc-native-edit';
            nativeBtn.title = 'Shortcut key: N';

            if (nativeBtn.tagName === 'INPUT') {
                nativeBtn.value = 'Edit (N)';
            } else {
                nativeBtn.textContent = 'Edit (N)';
            }

            nativeBtn.onclick = (event) => {
                window.pycmd('EFDRC!edit_native');
                event.preventDefault();
                event.stopPropagation();
            };

            editBtn.insertAdjacentElement('afterend', nativeBtn);
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
