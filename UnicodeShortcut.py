# -*- coding: utf-8 -*-
"""
Burp Unicode Shortcut Encoder/Decoder

Keybindings:
- Ctrl+N (Cmd+N on macOS): encode to \uXXXX
- Ctrl+Shift+N (Cmd+Shift+N): decode \uXXXX
"""
from burp import IBurpExtender, IExtensionStateListener          
from java.awt import KeyboardFocusManager, KeyEventDispatcher    
from java.awt.event import KeyEvent                              
from javax.swing import SwingUtilities                           
from javax.swing.text import JTextComponent                      
import re                                                        


class BurpExtender(IBurpExtender, IExtensionStateListener):
    def registerExtenderCallbacks(self, burp_callbacks):
        self.burp_callbacks = burp_callbacks
        burp_callbacks.setExtensionName("Unicode Shortcut Encoder/Decoder")

        self.key_dispatcher = _UnicodeKeyDispatcher(burp_callbacks)
        self.focus_manager = KeyboardFocusManager.getCurrentKeyboardFocusManager()
        self.focus_manager.addKeyEventDispatcher(self.key_dispatcher)

        burp_callbacks.registerExtensionStateListener(self)

    def extensionUnloaded(self):
        try:
            if getattr(self, "focus_manager", None) and getattr(self, "key_dispatcher", None):
                self.focus_manager.removeKeyEventDispatcher(self.key_dispatcher)
        except Exception:
            try:
                self.burp_callbacks.printError("Cleanup failed")
            except Exception:
                pass


class _UnicodeKeyDispatcher(KeyEventDispatcher):

    def __init__(self, burp_callbacks):
        self.burp_callbacks = burp_callbacks
        self.unicode_escape_pattern = re.compile(r"\\[uU][0-9A-Fa-f]{4}")

    def dispatchKeyEvent(self, key_event):
        try:
            if key_event.getID() != KeyEvent.KEY_PRESSED:
                return False
            if key_event.getKeyCode() != KeyEvent.VK_N:
                return False
            if not (key_event.isControlDown() or key_event.isMetaDown()):
                return False

            is_decode = key_event.isShiftDown()

            focused_component = KeyboardFocusManager.getCurrentKeyboardFocusManager().getFocusOwner()
            if focused_component is None or not isinstance(focused_component, JTextComponent):
                return False

            selected_text = focused_component.getSelectedText()
            selection_start = focused_component.getSelectionStart()
            selection_end = focused_component.getSelectionEnd()
            is_read_only_editor = (not focused_component.isEditable())

            if selected_text is None or len(selected_text) == 0:
                if is_read_only_editor:
                    input_text = focused_component.getText()
                    selection_start = 0
                    selection_end = len(input_text)
                else:
                    return False
            else:
                input_text = selected_text

            def apply_transformation():
                try:
                    transformed_text = self.decode_all(input_text) if is_decode else self.smart_encode(input_text)

                    if transformed_text == input_text:
                        return  

                    if is_read_only_editor:
                        self._show_popup(focused_component, ("Decode" if is_decode else "Encode"), transformed_text)
                    else:
                        focused_component.replaceRange(transformed_text, selection_start, selection_end)
                        focused_component.setSelectionStart(selection_start)
                        focused_component.setSelectionEnd(selection_start + len(transformed_text))
                except Exception as error:
                    try:
                        self.burp_callbacks.printError("Unicode transform error: %s" % error)
                    except Exception:
                        pass

            SwingUtilities.invokeLater(apply_transformation)
            key_event.consume()
            return True

        except Exception:
            return False

    def _tokenize(self, input_string):
        tokens = []
        scan_position = 0
        for match in self.unicode_escape_pattern.finditer(input_string):
            start_index, end_index = match.start(), match.end()
            if start_index > scan_position:
                tokens.append(("TXT", input_string[scan_position:start_index]))
            tokens.append(("ESC", match.group(0)))
            scan_position = end_index
        if scan_position < len(input_string):
            tokens.append(("TXT", input_string[scan_position:]))
        return tokens

    def _is_ascii_alnum(self, character):
        return ('A' <= character <= 'Z') or ('a' <= character <= 'z') or ('0' <= character <= '9')

    def _encode_cp(self, code_point):
        if code_point <= 0xFFFF:
            return "\\u%04X" % code_point
        code_offset = code_point - 0x10000
        high_surrogate = 0xD800 + (code_offset >> 10)
        low_surrogate = 0xDC00 + (code_offset & 0x3FF)
        return "\\u%04X\\u%04X" % (high_surrogate, low_surrogate)

    def smart_encode(self, input_string):
        tokens = self._tokenize(input_string)

        has_non_alnum = False
        for token_kind, token_value in tokens:
            if token_kind == "TXT":
                for character in token_value:
                    if not self._is_ascii_alnum(character):
                        has_non_alnum = True
                        break
                if has_non_alnum:
                    break

        encode_all_alnum = not has_non_alnum 

        output_parts = []
        for token_kind, token_value in tokens:
            if token_kind == "ESC":
                output_parts.append(token_value)
            else:
                if encode_all_alnum:
                    for character in token_value:
                        output_parts.append(self._encode_cp(ord(character)))
                else:
                    for character in token_value:
                        if self._is_ascii_alnum(character):
                            output_parts.append(character)
                        else:
                            output_parts.append(self._encode_cp(ord(character)))
        return "".join(output_parts)

    def decode_all(self, input_string):
        tokens = self._tokenize(input_string)
        decoded_parts = []
        token_index = 0
        while token_index < len(tokens):
            token_kind, token_value = tokens[token_index]
            if token_kind == "ESC":
                high_code_unit = int(token_value[2:], 16)

                if token_index + 1 < len(tokens) and tokens[token_index + 1][0] == "ESC":
                    if 0xD800 <= high_code_unit <= 0xDBFF:
                        low_code_unit = int(tokens[token_index + 1][1][2:], 16)
                        if 0xDC00 <= low_code_unit <= 0xDFFF:
                            code_point = 0x10000 + ((high_code_unit - 0xD800) << 10) + (low_code_unit - 0xDC00)
                            try:
                                decoded_parts.append(unichr(code_point))
                            except NameError:
                                decoded_parts.append(chr(code_point))
                            token_index += 2
                            continue

                if (0xD800 <= high_code_unit <= 0xDFFF) or (high_code_unit == 0xFFFE) or (high_code_unit == 0xFFFF):
                    decoded_parts.append(token_value)
                    token_index += 1
                    continue
                try:
                    decoded_parts.append(unichr(high_code_unit))
                except NameError:
                    decoded_parts.append(chr(high_code_unit))
                token_index += 1
            else:
                decoded_parts.append(token_value)
                token_index += 1
        return "".join(decoded_parts)

    def _show_popup(self, component_for_parent, action_label, result_text):
        from javax.swing import JDialog, JPanel, JButton
        from java.awt import BorderLayout
        from java.awt import Toolkit
        from java.awt.datatransfer import StringSelection
        from java.awt.event import ActionListener

        window_owner = SwingUtilities.getWindowAncestor(component_for_parent)
        dialog_title = "Unicode %s Result" % action_label
        dialog = JDialog(window_owner, dialog_title, True)  
        dialog.setDefaultCloseOperation(JDialog.DISPOSE_ON_CLOSE)

        burp_text_editor = self.burp_callbacks.createTextEditor()
        burp_text_editor.setEditable(False)
        try:
            editor_bytes = result_text.encode("utf-8")
        except Exception:
            editor_bytes = result_text
        burp_text_editor.setText(editor_bytes)

        dialog_panel = JPanel()
        dialog_panel.setLayout(BorderLayout())
        dialog_panel.add(burp_text_editor.getComponent(), BorderLayout.CENTER)

        class CopyAction(ActionListener):
            def actionPerformed(self, evt):
                try:
                    Toolkit.getDefaultToolkit().getSystemClipboard().setContents(StringSelection(result_text), None)
                except Exception:
                    pass

        class CloseAction(ActionListener):
            def actionPerformed(self, evt):
                dialog.dispose()

        copy_button = JButton("Copy to Clipboard")
        copy_button.addActionListener(CopyAction())
        close_button = JButton("Close")
        close_button.addActionListener(CloseAction())

        button_panel = JPanel()
        button_panel.add(copy_button)
        button_panel.add(close_button)
        dialog_panel.add(button_panel, BorderLayout.SOUTH)

        dialog.setContentPane(dialog_panel)
        dialog.setSize(600, 400)
        dialog.setLocationRelativeTo(window_owner)
        dialog.setVisible(True)
