# Unicode Shortcut
This extension adds **Unicode encode/decode** functionality to Burp Suite via custom shortcuts, making it easy to encode text to Unicode on the fly. It works by replacing your selected text with its encoded or decoded form. Just press **Ctrl+N** to **encode** and **Ctrl+Shift+N** to **decode**.
## Installation
- This extension is tested with **Jython 2.7.4**.
- Download `UnicodeShortcut.py` from the repository.
- Add it to Burp Suite using the `Extensions` tab.
## Features
### Works on selection
- Select the text you want to **encode** and press **Ctrl+N**.
- To **decode**, select the text and press **Ctrl+Shift+N**.
### Smart Encoding
Since reading Unicode directly can be difficult, the extension uses a two-step encoding process for alphanumeric strings mixed with other characters:
1. On the first **Ctrl+N**, only non-alphanumeric characters are encoded.
2. Pressing **Ctrl+N** again encodes all remaining alphanumeric characters.

`foo-bar.com` --> `foo\u002Dbar\u002Ecom` --> `\u0066\u006F\u006F\u002D\u0062\u0061\u0072\u002E\u0063\u006F\u006D`
### Convenient Decoding
- In **editable panels**, select Unicode text and press **ctrl+shift+n** to decode in place.
- In **read-only panels** for example response panel in repeater, pressing **ctrl+shift+n** opens a popup containing the decoded text.
	- If only a portion of the text should be decoded, select it first and then press the shortcut.
## To Do
- Make it easier to change shortcuts to other key combinations.
- Add pretty printing in the decode popup.
- Support additional encoding styles, such as `\xXX`.
