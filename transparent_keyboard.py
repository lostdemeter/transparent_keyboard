#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import sys
import transparent_keyboard_settings as settings
import subprocess
import pyperclip
import argparse

class TransparentKeyboard(tk.Tk):
    """
    A transparent, draggable virtual keyboard implementation.
    
    This class creates a virtual keyboard window with the following features:
    - Transparent window that can be dragged around the screen
    - QWERTY keyboard layout with special keys
    - Support for keyboard navigation using arrow keys
    - Caps lock functionality
    - Copy and paste support
    - Modern UI with customizable appearance through settings
    
    Command Line Arguments:
        --x: Window X position (default: 100)
        --y: Window Y position (default: 100)
        --width: Window width (default: 1200)
        --height: Window height (default: 400)
    
    Attributes:
        text_var (tk.StringVar): Stores the current input text
        caps_lock_on (bool): Tracks the state of caps lock
        buttons (List[List[tk.Button]]): 2D array of keyboard buttons
        current_row (int): Currently focused row in keyboard navigation
        current_col (int): Currently focused column in keyboard navigation
    """
    
    def __init__(self):
        """Initialize the virtual keyboard window and set up the UI components."""
        super().__init__()

        # Set window properties
        self.title("Virtual Keyboard")
        
        def on_escape(event: tk.Event) -> None:
            """Handle escape key press to close the window."""
            print("Escape key pressed")  # Debug print
            self.destroy()
        
        # Bind escape key to close the program
        self.bind('<Escape>', on_escape)
        self.bind_all('<Escape>', on_escape)  # Bind to all widgets
        
        # Bind arrow keys and enter for navigation
        self.bind_all('<Left>', lambda e: self.move_focus('left'))
        self.bind_all('<Right>', lambda e: self.move_focus('right'))
        self.bind_all('<Up>', lambda e: self.move_focus('up'))
        self.bind_all('<Down>', lambda e: self.move_focus('down'))
        self.bind_all('<Return>', lambda e: self.activate_focused())
        
        # Variables for window dragging
        self._drag_data = {"x": 0, "y": 0, "dragging": False}
        
        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Simplified QWERTY layout with Done and Cancel buttons
        self.keys = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '⌫'],
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['⇪', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', '↵'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '⨯'],
            ['⎵']
            
              # Cancel takes 3 columns, Done takes 9
        ]
        
        # Calculate window height based on the number of key rows and desired key height
        key_height = 60  # Increased from 40 to 60
        window_height = len(self.keys) * key_height + 80  # Increased padding from 50 to 80 for text display
        
        # Calculate window width
        window_width = int(screen_width * settings.KEYBOARD_WIDTH_RATIO)
        
        # Calculate position for center of screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set window size and position
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Configure window style for transparency
        if sys.platform.startswith('linux'):
            self.attributes('-type', 'dock')  # Use dock type instead of overrideredirect
            self.attributes('-alpha', 0.0)  # Start completely transparent
            self.attributes('-topmost', True)
        
        # Create main frame with black background and configure for dragging
        self.main_frame = tk.Frame(self, bg=settings.WINDOW_BACKGROUND_COLOR, cursor="fleur", highlightthickness=0)
        self.main_frame.pack(expand=True, fill='both', padx=0, pady=0)

        # Add text display at the top
        self.text_var = tk.StringVar()
        self.text_display = tk.Entry(self.main_frame, 
                                   textvariable=self.text_var,
                                   font=(settings.KEY_FONT_FAMILY, settings.KEY_FONT_SIZE),
                                   bg=settings.KEY_BACKGROUND_COLOR,
                                   fg=settings.KEY_TEXT_COLOR,
                                   insertbackground=settings.KEY_TEXT_COLOR,  # Cursor color
                                   relief='flat',
                                   highlightthickness=0,
                                   justify='center',
                                   cursor="fleur")  # Add cursor style for dragging
        self.text_display.pack(fill='x', padx=10, pady=10)

        # Create a frame for the keyboard with padding
        self.keyboard_frame = tk.Frame(self.main_frame, bg=settings.WINDOW_BACKGROUND_COLOR, cursor="fleur")
        self.keyboard_frame.pack(expand=True, fill='both', padx=10, pady=0)

        # Bind mouse events for window dragging to all draggable areas
        for widget in (self.main_frame, self.keyboard_frame, self.text_display):
            widget.bind('<Button-1>', self.start_drag)
            widget.bind('<B1-Motion>', self.on_drag)
            widget.bind('<ButtonRelease-1>', self.stop_drag)
        
        # Store buttons in a 2D array for navigation
        self.buttons = []
        self.current_row = 0
        self.current_col = 0
        
        # Configure grid columns to be uniform
        max_cols = max(len(row) for row in self.keys)
        for i in range(max_cols):
            self.keyboard_frame.grid_columnconfigure(i, weight=1, uniform='key')
        
        # Create and place buttons
        self.create_keyboard()
        
        # Update window size to fit all widgets
        self.update_idletasks()  # Ensure all widgets are rendered
        required_width = self.main_frame.winfo_reqwidth()
        required_height = self.main_frame.winfo_reqheight()
        
        # Add padding (more vertical padding)
        required_width += 20
        required_height += 60  # Increased from 20 to 60 for more vertical space
        
        # Update window size and center it on screen
        x = (screen_width - required_width) // 2
        y = (screen_height - required_height) // 2
        self.geometry(f"{required_width}x{required_height}+{x}+{y}")
        
        # Set initial focus
        if self.buttons and self.buttons[0]:
            self.buttons[0][0].configure(bg=settings.KEY_HOVER_COLOR)
        
        # Focus window once at the end
        self.focus_force()
        
        # Start fade in effect
        self.fade_in()
        
        # Add a state variable for Caps Lock
        self.caps_lock_on = False
        
        # Ensure initial keyboard layout is lowercase
        self.update_keyboard_layout()
        
        # Set up hover effects for all buttons
        self.setup_button_hover_effects()

    def fade_in(self, current_alpha=0.0):
        target_alpha = settings.WINDOW_TRANSPARENCY
        if current_alpha < target_alpha:
            current_alpha = min(current_alpha + 0.05, target_alpha)
            self.attributes('-alpha', current_alpha)
            self.after(10, lambda: self.fade_in(current_alpha))
        
    def create_keyboard(self):
        for row_idx, row in enumerate(self.keys):
            row_buttons = []
            for col_idx, key in enumerate(row):
                # Calculate button width for special keys
                width = 1
                if key == '⌫':
                    width = settings.BACKSPACE_KEY_WIDTH
                elif key == '↵':
                    width = settings.ENTER_KEY_WIDTH
                elif key == '⎵':
                    width = settings.SPACE_KEY_WIDTH
                elif key == '⨯':
                    width = settings.CANCEL_KEY_WIDTH
                
                # Ensure width is an integer
                width = int(width)
                
                # Create button with modern styling
                font_size = settings.SPECIAL_KEY_FONT_SIZE if width > 1 else settings.KEY_FONT_SIZE
                button_font = (settings.KEY_FONT_FAMILY, font_size)
                
                # Set background color based on key type
                bg_color = settings.KEY_BACKGROUND_COLOR
                if key == '⨯':
                    bg_color = settings.CANCEL_KEY_COLOR
                
                # Calculate row width for centering
                row_width = sum(self.get_key_width(k) for k in row)
                max_width = 12  # Total grid columns
                
                # Center the M row and position Cancel key
                if row_idx == 3:  # M row
                    start_column = (max_width - row_width) // 2
                    if key == '⨯':
                        start_column = 10  # Align with return key
                elif row_idx >= 4:  # Space row
                    if key == '⎵':
                        start_column = 1
                        width = settings.SPACE_KEY_WIDTH
                else:
                    start_column = 0
                
                # Manually center Space and Cancel keys
                if row_idx >= 4:  # For Space and Cancel rows
                    total_cols = 12  # Total grid columns
                    
                    # Calculate positions for Space and Cancel buttons
                    if key == '⎵':
                        start_column = 1  # Start from column 1
                        width = settings.SPACE_KEY_WIDTH
                    elif key == '⨯':
                        start_column = 9  # Position under the return key
                        width = settings.CANCEL_KEY_WIDTH
                    
                    button = tk.Button(self.keyboard_frame, text=key,
                                  command=lambda k=key: self.key_press(k),
                                  bg=bg_color,
                                  fg=settings.KEY_TEXT_COLOR,
                                  activebackground=settings.KEY_HOVER_COLOR,
                                  activeforeground=settings.KEY_TEXT_COLOR,
                                  font=button_font,
                                  relief='flat',
                                  bd=settings.KEY_BORDER_WIDTH,
                                  padx=settings.KEY_PADDING_X,
                                  pady=settings.KEY_PADDING_Y,
                                  width=4 if width == 1 else width * 4,  # Set fixed character width
                                  highlightthickness=0)
                    
                    button.grid(row=row_idx + 1, 
                            column=start_column,
                            columnspan=width,
                            padx=settings.KEY_MARGIN,  # Removed extra padding between buttons
                            pady=settings.KEY_MARGIN,
                            sticky='nsew')
                    
                    # Bind Enter key to Cancel button
                    if key == '⨯':
                        button.bind('<Return>', lambda e: self.key_press('⨯'))
                    
                    # Bind focus out event to reset button color
                    button.bind('<FocusOut>', lambda e, b=button, c=bg_color: b.configure(bg=c))
                else:
                    # Original grid placement for other rows
                    button = tk.Button(self.keyboard_frame, text=key,
                                  command=lambda k=key: self.key_press(k),
                                  bg=bg_color,
                                  fg=settings.KEY_TEXT_COLOR,
                                  activebackground=settings.KEY_HOVER_COLOR,
                                  activeforeground=settings.KEY_TEXT_COLOR,
                                  font=button_font,
                                  relief='flat',
                                  bd=settings.KEY_BORDER_WIDTH,
                                  padx=settings.KEY_PADDING_X,
                                  pady=settings.KEY_PADDING_Y,
                                  width=4 if width == 1 else width * 4,  # Set fixed character width
                                  highlightthickness=0)
                    
                    # Position buttons with special handling for Cancel key
                    if row_idx == 3 and key == '⨯':
                        button.grid(row=row_idx + 1,
                                column=10,  # Align with return key
                                columnspan=width,
                                padx=settings.KEY_MARGIN,
                                pady=settings.KEY_MARGIN,
                                sticky='nsew')
                    else:
                        button.grid(row=row_idx + 1, 
                                column=col_idx + start_column if row_idx == 3 else col_idx,
                                columnspan=width,
                                padx=settings.KEY_MARGIN,
                                pady=settings.KEY_MARGIN,
                                sticky='nsew')
                
                row_buttons.append(button)
            self.buttons.append(row_buttons)
        
        # Update the Caps button appearance based on its state
        caps_button = self.buttons[2][0]  # Assuming Caps is at row 2, column 0
        caps_button.configure(command=self.toggle_caps_lock)
    
    def key_press(self, key: str) -> None:
        """
        Handle key press events from the virtual keyboard.
        
        This method processes different types of key presses:
        - Regular characters: Added to the input text
        - Special keys: Handled according to their function (backspace, space, etc.)
        - Return key: Copies text to clipboard and simulates paste
        - Cancel key: Clears text and closes the window
        
        Args:
            key: The key character or symbol that was pressed
        """
        current_text = self.text_var.get()
        
        if key == '⨯':  # Cancel
            self.text_var.set('')  # Clear the text
            self.destroy()
        elif key == '⌫':  # Backspace
            self.text_var.set(current_text[:-1])
        elif key == '⎵':  # Space
            self.text_var.set(current_text + ' ')
        elif key.lower() == '⇪':  # Handle both '⇪' and '⇪'
            self.toggle_caps_lock()
        elif key == '↵':  # Return key
            if current_text:
                # Copy text to clipboard
                pyperclip.copy(current_text)
                
                # Run subprocess to paste the text
                try:
                    subprocess.Popen(['xdotool', 'key', 'ctrl+v'])
                except FileNotFoundError:
                    print("Error: xdotool not found. Please install xdotool package.")
                except Exception as e:
                    print(f"Error running xdotool: {e}")
            
            self.destroy()
            return
        
        # Handle letter keys according to caps lock state
        elif key.isalpha():
            if self.caps_lock_on:
                key = key.upper()
            else:
                key = key.lower()
            self.text_var.set(current_text + key)
        
        # For other keys (symbols, numbers), add them as they are
        elif not key in ['⌫', '⎵', '⨯', '↵', '⇪']:
            self.text_var.set(current_text + key)

    def move_focus(self, direction: str) -> None:
        """
        Move the keyboard focus in the specified direction.
        
        Handles keyboard navigation using arrow keys, wrapping around edges
        and finding the closest button when moving between rows of different lengths.
        
        Args:
            direction: Direction to move ('left', 'right', 'up', 'down')
        """
        # Remove focus from current button
        self.reset_button_color(self.buttons[self.current_row][self.current_col],
                              self.keys[self.current_row][self.current_col])
        
        # Calculate new position
        if direction == 'left':
            self.current_col = (self.current_col - 1) % len(self.buttons[self.current_row])
        elif direction == 'right':
            self.current_col = (self.current_col + 1) % len(self.buttons[self.current_row])
        elif direction == 'up' or direction == 'down':
            # Get current button's grid info
            current_button = self.buttons[self.current_row][self.current_col]
            current_x = current_button.grid_info()['column']
            
            # Calculate new row
            new_row = (self.current_row - 1) if direction == 'up' else (self.current_row + 1)
            new_row = new_row % len(self.buttons)
            
            # Find the closest button in the new row
            closest_col = 0
            min_distance = float('inf')
            for col, button in enumerate(self.buttons[new_row]):
                button_x = button.grid_info()['column']
                distance = abs(button_x - current_x)
                if distance < min_distance:
                    min_distance = distance
                    closest_col = col
            
            self.current_row = new_row
            self.current_col = closest_col
        
        # Set focus on new button
        focused_button = self.buttons[self.current_row][self.current_col]
        focused_button.configure(bg=settings.KEY_HOVER_COLOR)
    
    def activate_focused(self, event=None):
        """Simulate clicking the currently focused button and ensure keyboard focus"""
        # Ensure the keyboard window is raised and has focus
        self.lift()  # Bring window to the top
        self.focus_force()  # Force focus on the keyboard window
        
        button = self.buttons[self.current_row][self.current_col]
        key = button.cget('text')  # Get the button's text
        
        # Handle Cancel button to exit the program
        if key == '⨯':
            self.destroy()
            return
        elif key == '↵':  # Return key
            current_text = self.text_var.get()
            if current_text:
                # Copy text to clipboard
                pyperclip.copy(current_text)
                
                # Run subprocess to paste the text
                try:
                    subprocess.Popen(['xdotool', 'key', 'ctrl+v'])
                except Exception as e:
                    print(f"Error running xdotool: {e}")
            
            self.destroy()
            return
        
        # Handle caps lock toggle
        if key.lower() == '⇪':  # Handle both '⇪' and '⇪'
            self.toggle_caps_lock()
            return
        
        # Add the key's text to the input field
        self.key_press(key)
    
    def get_key_width(self, key: str) -> int:
        """
        Get the width (in grid columns) for a given key.
        
        Args:
            key: The key character or symbol
            
        Returns:
            The width of the key in grid columns
        """
        if key == '⌫':
            return settings.BACKSPACE_KEY_WIDTH
        elif key == '↵':
            return settings.ENTER_KEY_WIDTH
        elif key == '⎵':
            return settings.SPACE_KEY_WIDTH
        elif key == '⨯':
            return settings.CANCEL_KEY_WIDTH
        return 1

    def reset_button_color(self, button: tk.Button, key: str) -> None:
        """
        Reset a button's background color to its default state.
        
        Args:
            button: The button widget to reset
            key: The key character or symbol of the button
        """
        if key == '⨯':
            button.configure(bg=settings.CANCEL_KEY_COLOR)
        else:
            button.configure(bg=settings.KEY_BACKGROUND_COLOR)

    def toggle_caps_lock(self) -> None:
        """
        Toggle the caps lock state and update the keyboard layout.
        
        Updates the caps lock button appearance and converts all letter keys
        to their appropriate case.
        """
        self.caps_lock_on = not self.caps_lock_on
        caps_button = self.buttons[2][0]  # Caps is at row 2, column 0
        
        if self.caps_lock_on:
            caps_button.configure(text='⇪', bg=settings.KEY_HOVER_COLOR)
        else:
            caps_button.configure(text='⇪', bg=settings.KEY_BACKGROUND_COLOR)
            self.current_row = 2
            self.current_col = 0
            
        self.update_keyboard_layout()

    def setup_button_hover_effects(self) -> None:
        """Set up mouse hover effects for all keyboard buttons."""
        for row in self.buttons:
            for button in row:
                button.bind('<Enter>', lambda e, btn=button: self.on_button_enter(btn))
                button.bind('<Leave>', lambda e, btn=button: self.on_button_leave(btn))

    def on_button_enter(self, button: tk.Button) -> None:
        """
        Handle mouse enter event for buttons.
        
        Args:
            button: The button that triggered the event
        """
        if (button != self.buttons[self.current_row][self.current_col] and 
            button != self.buttons[2][0]):  # Not current focus or Caps Lock
            button.configure(bg=settings.KEY_HOVER_COLOR)

    def on_button_leave(self, button: tk.Button) -> None:
        """
        Handle mouse leave event for buttons.
        
        Args:
            button: The button that triggered the event
        """
        if (button != self.buttons[self.current_row][self.current_col] and 
            button != self.buttons[2][0]):  # Not current focus or Caps Lock
            button.configure(bg=settings.KEY_BACKGROUND_COLOR)

    def update_keyboard_layout(self):
        """Update the keyboard layout based on caps lock state"""
        for row_idx, row in enumerate(self.buttons):
            for col_idx, button in enumerate(row):
                # Update button text based on caps lock state
                key_text = button.cget('text')
                if key_text.isalpha():
                    if self.caps_lock_on:
                        button.configure(text=key_text.upper())
                    else:
                        button.configure(text=key_text.lower())
                
                # Set button color
                if row_idx == self.current_row and col_idx == self.current_col:
                    button.configure(bg=settings.KEY_HOVER_COLOR)
                else:
                    button.configure(bg=settings.KEY_BACKGROUND_COLOR)

    def start_drag(self, event: tk.Event) -> None:
        """
        Begin window dragging operation.
        
        Only starts dragging if clicking on the frame, not on buttons.
        
        Args:
            event: The mouse event that triggered the drag
        """
        if event.widget in (self.main_frame, self.keyboard_frame, self.text_display):
            self._drag_data["x"] = event.x
            self._drag_data["y"] = event.y
            self._drag_data["dragging"] = True

    def on_drag(self, event: tk.Event) -> None:
        """
        Handle window dragging motion.
        
        Updates the window position based on mouse movement.
        
        Args:
            event: The mouse motion event
        """
        if (self._drag_data["dragging"] and 
            event.widget in (self.main_frame, self.keyboard_frame, self.text_display)):
            # Calculate the distance moved
            dx = event.x - self._drag_data["x"]
            dy = event.y - self._drag_data["y"]
            
            # Get the current window position
            x = self.winfo_x() + dx
            y = self.winfo_y() + dy
            
            # Move the window
            self.geometry(f"+{x}+{y}")

    def stop_drag(self, event: tk.Event) -> None:
        """
        End window dragging operation.
        
        Args:
            event: The mouse event that ended the drag
        """
        self._drag_data["dragging"] = False
        self.focus_force()  # Force focus back to the window after dragging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transparent Keyboard')
    parser.add_argument('--x', type=int, help='Window X position', default=100)
    parser.add_argument('--y', type=int, help='Window Y position', default=100)
    parser.add_argument('--width', type=int, help='Window width', default=1200)
    parser.add_argument('--height', type=int, help='Window height', default=400)
    
    args = parser.parse_args()
    
    app = TransparentKeyboard()
    app.geometry(f"{args.width}x{args.height}+{args.x}+{args.y}")
    app.mainloop()
