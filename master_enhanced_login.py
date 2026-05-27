import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from master_backend_api_client import MasterBackendAPIClient

class _AutoSizeStack(QStackedWidget):
    """QStackedWidget that reports the current page's natural size, not the max of all pages."""

    def sizeHint(self):
        w = self.currentWidget()
        return w.sizeHint() if w else super().sizeHint()

    def minimumSizeHint(self):
        w = self.currentWidget()
        return w.minimumSizeHint() if w else super().minimumSizeHint()


class MasterEnhancedLoginDialog(QDialog):
    """Enhanced login dialog with email authentication and dark theme."""
    
    login_success = pyqtSignal(str, dict)  # email, user_profile
    
    def __init__(self, parent=None):
        # QDialog requires parent to be QWidget or None; use None when parent is not a widget
        from PyQt5.QtWidgets import QWidget
        dialog_parent = parent if isinstance(parent, QWidget) else None
        super().__init__(dialog_parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Use parent's API client only when parent is a QWidget with api_client (e.g. MainWindow)
        if isinstance(parent, QWidget) and hasattr(parent, 'api_client'):
            self.api_client = parent.api_client
            print(f"Using parent's API client instance: {id(self.api_client)}")
        else:
            self.api_client = MasterBackendAPIClient()
            print(f"Created new API client instance: {id(self.api_client)}")
        
        self.current_view = "login"
        self.reset_token = None
        
        self.setWindowTitle("ROBOX - User Authentication")
        _icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "Absix_logo.png")
        if os.path.exists(_icon_path):
            self.setWindowIcon(QIcon(_icon_path))
        self.setModal(True)
        
        self.setWindowFlags(
            Qt.Dialog |
            Qt.WindowTitleHint |
            Qt.WindowCloseButtonHint |
            Qt.WindowMinimizeButtonHint
        )

        self.setup_ui()
        self.apply_styling()

        self.setMinimumWidth(720)
        self.adjustSize()
        self.center_on_screen()
    
    def setup_ui(self):
        """Set up the user interface."""
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()

        # Add views directly — no scroll wrappers so the dialog auto-sizes per view
        self.login_widget = self.create_login_view()
        self.register_widget = self.create_register_view()
        self.forgot_password_widget = self.create_forgot_password_view()
        self.reset_password_widget = self.create_reset_password_view()
        self.verification_widget = self.create_verification_view()

        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.register_widget)
        self.stacked_widget.addWidget(self.forgot_password_widget)
        self.stacked_widget.addWidget(self.reset_password_widget)
        self.stacked_widget.addWidget(self.verification_widget)

        self.main_layout.addWidget(self.stacked_widget)
        self.setLayout(self.main_layout)

    def _is_valid_email(self, email: str) -> bool:
        email = email.strip().lower()
        if "@" not in email:
            return False
        local, _, domain = email.partition("@")
        if not local or not domain or "." not in domain:
            return False
        return True
    
    def _add_logo(self, layout, height=56):
        """Add the ROBOX logo in a pill container with glow and a gradient divider."""
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        from PyQt5.QtGui import QColor

        # Pill container
        pill = QFrame()
        pill.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                border-radius: 18px;
            }
        """)
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(24, 10, 24, 10)
        pill_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_label.setAttribute(Qt.WA_TranslucentBackground)
        logo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "resources", "AB6_Logo.png"
        )
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaledToHeight(height, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("background: transparent; border: none;")

        # Soft white glow around the logo image
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(28)
        glow.setColor(QColor(255, 255, 255, 55))
        glow.setOffset(0, 0)
        logo_label.setGraphicsEffect(glow)

        pill_layout.addWidget(logo_label)

        # Centre the pill horizontally
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch()
        row.addWidget(pill)
        row.addStretch()
        layout.addLayout(row)

        # Gradient divider line below the pill
        divider = QFrame()
        divider.setFixedHeight(3)
        divider.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0    rgba(255,255,255,0),
                    stop:0.18 rgba(255,255,255,0.12),
                    stop:0.35 rgba(255,255,255,0.70),
                    stop:0.50 rgba(255,255,255,0.95),
                    stop:0.65 rgba(255,255,255,0.70),
                    stop:0.82 rgba(255,255,255,0.12),
                    stop:1    rgba(255,255,255,0)
                );
                border: none;
                border-radius: 1px;
            }
        """)
        layout.addSpacing(8)
        layout.addWidget(divider)

    def _wrap_in_scroll(self, widget):
        """Wrap a widget in a scroll area for better display on small screens."""
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        return scroll
    
    def create_login_view(self):
        """Create login view."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(40, 24, 40, 24)

        self._add_logo(layout, height=56)
        layout.addSpacing(10)

        title = QLabel("Welcome Back")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addSpacing(4)

        subtitle = QLabel("Sign in to your account")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(16)

        form_frame = QFrame()
        form_frame.setObjectName("form")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(0)
        form_layout.setContentsMargins(24, 22, 24, 22)

        email_label = QLabel("Email Address")
        email_label.setObjectName("field_label")
        self.login_email_edit = QLineEdit()
        self.login_email_edit.setPlaceholderText("you@example.com")
        self.login_email_edit.setObjectName("input_field")
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.login_email_edit)
        form_layout.addSpacing(14)

        password_label = QLabel("Password")
        password_label.setObjectName("field_label")
        self.login_password_edit = QLineEdit()
        self.login_password_edit.setPlaceholderText("Enter your password")
        self.login_password_edit.setEchoMode(QLineEdit.Password)
        self.login_password_edit.setObjectName("input_field")
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.login_password_edit)
        form_layout.addSpacing(6)

        forgot_link = QPushButton("Forgot your password?")
        forgot_link.setObjectName("link_button")
        forgot_link.clicked.connect(lambda: self.switch_view("forgot_password"))
        form_layout.addWidget(forgot_link, 0, Qt.AlignRight)
        form_layout.addSpacing(10)

        login_action_row = QHBoxLayout()
        login_action_row.setSpacing(12)
        login_btn = QPushButton("Sign In")
        login_btn.setObjectName("primary_button")
        login_btn.clicked.connect(self.handle_login)
        register_link = QPushButton("New here? Create an Account")
        register_link.setObjectName("link_button")
        register_link.clicked.connect(lambda: self.switch_view("register"))
        login_action_row.addWidget(login_btn, 3)
        login_action_row.addWidget(register_link, 2)
        form_layout.addLayout(login_action_row)

        layout.addWidget(form_frame)

        widget.setTabOrder(self.login_email_edit, self.login_password_edit)
        self.login_email_edit.returnPressed.connect(self.login_password_edit.setFocus)
        self.login_password_edit.returnPressed.connect(self.handle_login)

        widget.setLayout(layout)
        return widget
        
    def create_register_view(self):
        """Create registration view."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(40, 14, 40, 14)

        self._add_logo(layout, height=36)
        layout.addSpacing(8)

        title = QLabel("Create Account")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addSpacing(4)

        subtitle = QLabel("Join the ROBOX robotics platform")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        form_frame = QFrame()
        form_frame.setObjectName("form")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(0)
        form_layout.setContentsMargins(24, 20, 24, 20)

        # Row 1: Full Name | College / Institution
        row1 = QHBoxLayout()
        row1.setSpacing(14)

        name_col = QVBoxLayout()
        name_col.setSpacing(8)
        name_label = QLabel("Full Name")
        name_label.setObjectName("field_label")
        self.register_name_edit = QLineEdit()
        self.register_name_edit.setPlaceholderText("Enter your full name")
        self.register_name_edit.setObjectName("input_field")
        name_col.addWidget(name_label)
        name_col.addWidget(self.register_name_edit)

        college_col = QVBoxLayout()
        college_col.setSpacing(8)
        college_label = QLabel("College / Institution")
        college_label.setObjectName("field_label")
        self.register_college_edit = QLineEdit()
        self.register_college_edit.setPlaceholderText("Enter your college name")
        self.register_college_edit.setObjectName("input_field")
        college_col.addWidget(college_label)
        college_col.addWidget(self.register_college_edit)

        row1.addLayout(name_col)
        row1.addLayout(college_col)
        form_layout.addLayout(row1)
        form_layout.addSpacing(14)

        # Row 2: Email Address | Mobile Number
        row2 = QHBoxLayout()
        row2.setSpacing(14)

        email_col = QVBoxLayout()
        email_col.setSpacing(8)
        email_label = QLabel("Email Address")
        email_label.setObjectName("field_label")
        self.register_email_edit = QLineEdit()
        self.register_email_edit.setPlaceholderText("you@example.com")
        self.register_email_edit.setObjectName("input_field")
        email_col.addWidget(email_label)
        email_col.addWidget(self.register_email_edit)

        mobile_col = QVBoxLayout()
        mobile_col.setSpacing(8)
        mobile_label = QLabel("Mobile Number")
        mobile_label.setObjectName("field_label")
        self.register_mobile_edit = QLineEdit()
        self.register_mobile_edit.setPlaceholderText("10-digit mobile number")
        self.register_mobile_edit.setObjectName("input_field")
        self.register_mobile_edit.setMaxLength(10)
        self.register_mobile_edit.setValidator(QIntValidator())
        mobile_col.addWidget(mobile_label)
        mobile_col.addWidget(self.register_mobile_edit)

        row2.addLayout(email_col)
        row2.addLayout(mobile_col)
        form_layout.addLayout(row2)
        form_layout.addSpacing(14)

        # Row 3: Password | Confirm Password
        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(14)

        pwd_col = QVBoxLayout()
        pwd_col.setSpacing(8)
        password_label = QLabel("Password")
        password_label.setObjectName("field_label")
        self.register_password_edit = QLineEdit()
        self.register_password_edit.setPlaceholderText("Min. 8 characters")
        self.register_password_edit.setEchoMode(QLineEdit.Password)
        self.register_password_edit.setObjectName("input_field")
        self.register_password_edit.textChanged.connect(self.update_password_strength)
        self.password_strength_label = QLabel("")
        self.password_strength_label.setObjectName("password_strength")
        pwd_col.addWidget(password_label)
        pwd_col.addWidget(self.register_password_edit)
        pwd_col.addWidget(self.password_strength_label)

        confirm_col = QVBoxLayout()
        confirm_col.setSpacing(8)
        confirm_label = QLabel("Confirm Password")
        confirm_label.setObjectName("field_label")
        self.register_confirm_edit = QLineEdit()
        self.register_confirm_edit.setPlaceholderText("Re-enter your password")
        self.register_confirm_edit.setEchoMode(QLineEdit.Password)
        self.register_confirm_edit.setObjectName("input_field")
        confirm_col.addWidget(confirm_label)
        confirm_col.addWidget(self.register_confirm_edit)
        confirm_col.addStretch()

        pwd_row.addLayout(pwd_col)
        pwd_row.addLayout(confirm_col)
        form_layout.addLayout(pwd_row)
        form_layout.addSpacing(12)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        register_btn = QPushButton("Create Account")
        register_btn.setObjectName("primary_button")
        register_btn.clicked.connect(self.handle_register)

        sign_in_col = QVBoxLayout()
        sign_in_col.setSpacing(2)
        sign_in_col.setAlignment(Qt.AlignCenter)
        back_label = QLabel("Already have an account?")
        back_label.setObjectName("small_text")
        back_label.setAlignment(Qt.AlignCenter)
        back_link = QPushButton("Sign In")
        back_link.setObjectName("link_button")
        back_link.clicked.connect(lambda: self.switch_view("login"))
        sign_in_col.addWidget(back_label)
        sign_in_col.addWidget(back_link)

        btn_row.addWidget(register_btn, 3)
        btn_row.addLayout(sign_in_col, 2)
        form_layout.addLayout(btn_row)

        layout.addWidget(form_frame)

        self.register_name_edit.returnPressed.connect(self.register_college_edit.setFocus)
        self.register_college_edit.returnPressed.connect(self.register_email_edit.setFocus)
        self.register_email_edit.returnPressed.connect(self.register_mobile_edit.setFocus)
        self.register_mobile_edit.returnPressed.connect(self.register_password_edit.setFocus)
        self.register_password_edit.returnPressed.connect(self.register_confirm_edit.setFocus)
        self.register_confirm_edit.returnPressed.connect(self.handle_register)

        widget.setLayout(layout)
        return widget
    
    def create_forgot_password_view(self):
        """Create forgot password view."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(40, 14, 40, 14)

        self._add_logo(layout, height=56)
        layout.addSpacing(6)

        title = QLabel("Reset Password")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addSpacing(2)

        desc = QLabel("Enter your email and we'll send you a reset code.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setObjectName("subtitle")
        layout.addWidget(desc)
        layout.addSpacing(10)

        form_frame = QFrame()
        form_frame.setObjectName("form")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(0)
        form_layout.setContentsMargins(28, 30, 28, 30)

        email_label = QLabel("Email Address")
        email_label.setObjectName("field_label")
        self.forgot_email_edit = QLineEdit()
        self.forgot_email_edit.setPlaceholderText("you@example.com")
        self.forgot_email_edit.setObjectName("input_field")
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.forgot_email_edit)
        form_layout.addSpacing(28)

        reset_btn = QPushButton("Send Reset Code")
        reset_btn.setObjectName("primary_button")
        reset_btn.clicked.connect(self.handle_forgot_password)
        form_layout.addWidget(reset_btn)
        form_layout.addSpacing(10)

        back_link = QPushButton("← Back to Sign In")
        back_link.setObjectName("link_button")
        back_link.clicked.connect(lambda: self.switch_view("login"))
        form_layout.addWidget(back_link, 0, Qt.AlignCenter)

        layout.addWidget(form_frame)
        widget.setLayout(layout)
        return widget

    def create_reset_password_view(self):
        """Create reset password view."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(40, 24, 40, 24)

        self._add_logo(layout, height=56)
        layout.addSpacing(10)

        title = QLabel("Set New Password")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addSpacing(4)

        desc = QLabel("Enter the reset code from your email and choose a new password.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setObjectName("subtitle")
        layout.addWidget(desc)
        layout.addSpacing(16)

        form_frame = QFrame()
        form_frame.setObjectName("form")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(0)
        form_layout.setContentsMargins(24, 22, 24, 22)

        code_label = QLabel("Reset Code")
        code_label.setObjectName("field_label")
        self.reset_code_edit = QLineEdit()
        self.reset_code_edit.setPlaceholderText("Code from your email")
        self.reset_code_edit.setObjectName("input_field")
        form_layout.addWidget(code_label)
        form_layout.addWidget(self.reset_code_edit)
        form_layout.addSpacing(14)

        # New Password + Confirm — side by side
        reset_pwd_row = QHBoxLayout()
        reset_pwd_row.setSpacing(14)

        new_pwd_col = QVBoxLayout()
        new_pwd_col.setSpacing(8)
        password_label = QLabel("New Password")
        password_label.setObjectName("field_label")
        self.reset_password_edit = QLineEdit()
        self.reset_password_edit.setPlaceholderText("Min. 8 characters")
        self.reset_password_edit.setEchoMode(QLineEdit.Password)
        self.reset_password_edit.setObjectName("input_field")
        new_pwd_col.addWidget(password_label)
        new_pwd_col.addWidget(self.reset_password_edit)

        confirm_pwd_col = QVBoxLayout()
        confirm_pwd_col.setSpacing(8)
        confirm_label = QLabel("Confirm New Password")
        confirm_label.setObjectName("field_label")
        self.reset_confirm_edit = QLineEdit()
        self.reset_confirm_edit.setPlaceholderText("Re-enter new password")
        self.reset_confirm_edit.setEchoMode(QLineEdit.Password)
        self.reset_confirm_edit.setObjectName("input_field")
        confirm_pwd_col.addWidget(confirm_label)
        confirm_pwd_col.addWidget(self.reset_confirm_edit)

        reset_pwd_row.addLayout(new_pwd_col)
        reset_pwd_row.addLayout(confirm_pwd_col)
        form_layout.addLayout(reset_pwd_row)
        form_layout.addSpacing(16)

        reset_btn_row = QHBoxLayout()
        reset_btn_row.setSpacing(12)
        reset_btn = QPushButton("Update Password")
        reset_btn.setObjectName("primary_button")
        reset_btn.clicked.connect(self.handle_reset_password)
        back_link = QPushButton("← Back to Sign In")
        back_link.setObjectName("link_button")
        back_link.clicked.connect(lambda: self.switch_view("login"))
        reset_btn_row.addWidget(reset_btn, 3)
        reset_btn_row.addWidget(back_link, 2)
        form_layout.addLayout(reset_btn_row)

        layout.addWidget(form_frame)
        widget.setLayout(layout)
        return widget

    def create_verification_view(self):
        """Create email verification view with terms agreement."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(40, 20, 40, 20)

        self._add_logo(layout, height=56)
        layout.addSpacing(8)

        title = QLabel("Verify Your Email")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addSpacing(4)

        self.verification_message = QLabel("")
        self.verification_message.setAlignment(Qt.AlignCenter)
        self.verification_message.setWordWrap(True)
        self.verification_message.setObjectName("subtitle")
        layout.addWidget(self.verification_message)
        layout.addSpacing(10)

        terms_frame = QFrame()
        terms_frame.setObjectName("terms_notice")
        terms_layout = QVBoxLayout(terms_frame)
        terms_layout.setSpacing(6)
        terms_layout.setContentsMargins(14, 12, 14, 12)

        terms_title = QLabel("Terms & Conditions")
        terms_title.setObjectName("terms_title")
        terms_title.setAlignment(Qt.AlignCenter)

        terms_notice = QLabel(
            "By verifying below you confirm you have read and agree to the ROBOX "
            "Terms and Conditions sent to your email."
        )
        terms_notice.setWordWrap(True)
        terms_notice.setObjectName("terms_text")
        terms_notice.setAlignment(Qt.AlignCenter)

        terms_layout.addWidget(terms_title)
        terms_layout.addWidget(terms_notice)
        layout.addWidget(terms_frame)
        layout.addSpacing(12)

        manual_frame = QFrame()
        manual_frame.setObjectName("form")
        manual_layout = QVBoxLayout(manual_frame)
        manual_layout.setSpacing(0)
        manual_layout.setContentsMargins(24, 20, 24, 20)

        manual_label = QLabel("Verification Code")
        manual_label.setObjectName("field_label")
        self.verification_code_edit = QLineEdit()
        self.verification_code_edit.setPlaceholderText("Code from your email")
        self.verification_code_edit.setObjectName("input_field")
        manual_layout.addWidget(manual_label)
        manual_layout.addWidget(self.verification_code_edit)
        manual_layout.addSpacing(10)

        self.terms_checkbox = QCheckBox()
        self.terms_checkbox.setObjectName("terms_checkbox")
        terms_checkbox_label = QLabel("I agree to the Terms & Conditions, Privacy Policy, and User Agreement")
        terms_checkbox_label.setWordWrap(True)
        terms_checkbox_label.setObjectName("checkbox_label")
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(8)
        checkbox_layout.addWidget(self.terms_checkbox)
        checkbox_layout.addWidget(terms_checkbox_label)
        manual_layout.addLayout(checkbox_layout)
        manual_layout.addSpacing(12)

        verify_btn = QPushButton("Verify & Accept Terms")
        verify_btn.setObjectName("primary_button")
        verify_btn.clicked.connect(self.handle_manual_verification)
        manual_layout.addWidget(verify_btn)

        layout.addWidget(manual_frame)
        layout.addSpacing(10)

        self.resend_status_label = QLabel("")
        self.resend_status_label.setAlignment(Qt.AlignCenter)
        self.resend_status_label.setObjectName("small_text")
        layout.addWidget(self.resend_status_label)
        layout.addSpacing(4)

        verif_nav_row = QHBoxLayout()
        verif_nav_row.setContentsMargins(0, 0, 0, 0)
        verif_nav_row.setSpacing(6)
        self.resend_verification_button = QPushButton("Resend Verification Email")
        self.resend_verification_button.setObjectName("link_button")
        self.resend_verification_button.clicked.connect(self.handle_resend_verification)
        back_link = QPushButton("← Back to Sign In")
        back_link.setObjectName("link_button")
        back_link.clicked.connect(lambda: self.switch_view("login"))
        verif_nav_row.addStretch()
        verif_nav_row.addWidget(self.resend_verification_button)
        verif_nav_row.addWidget(back_link)
        verif_nav_row.addStretch()
        layout.addLayout(verif_nav_row)

        widget.setLayout(layout)
        return widget
        
    def get_user_ip(self):
        """Get user's IP address for legal record keeping."""
        import socket
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except Exception:
            return "unknown"

    def handle_manual_verification(self):
        """Handle manual verification with terms agreement."""
        token = self.verification_code_edit.text().strip()
        
        if hasattr(self, 'terms_checkbox'):
            terms_agreed = self.terms_checkbox.isChecked()
            if not terms_agreed:
                self.show_message("Terms Required", 
                                "You must agree to the Terms and Conditions to complete registration", 
                                QMessageBox.Warning)
                return
        
        if not token:
            self.show_message("Error", "Please enter the verification code", QMessageBox.Warning)
            return
        
        self.show_loading("Verifying email and processing terms agreement...")
        QTimer.singleShot(100, lambda: self._do_verify_email_with_terms(token))
        
    def _do_verify_email_with_terms(self, token):
        """Perform email verification. Terms will be accepted at first login."""
        email = getattr(self, 'verification_email', '')
        success, message = self.api_client.verify_email(email, token)
        
        self.hide_loading()
        
        if success:
            self.show_message("Success", 
                            "Email verified successfully! You can now sign in. "
                        "You will be asked to accept terms and conditions on your first login.", 
                            QMessageBox.Information)
            self.switch_view("login")
        else:
            self.show_message("Verification Failed", message, QMessageBox.Critical)
            
    def record_terms_acceptance(self):
        """Record terms acceptance using secure database storage."""
        try:
            success, message = self.api_client.accept_terms()
            return success
        except Exception:
            return False

    def switch_view(self, view_name):
        """Switch to different view."""
        self.current_view = view_name
        
        if view_name == "login":
            self.stacked_widget.setCurrentWidget(self.login_widget)
        elif view_name == "register":
            self.stacked_widget.setCurrentWidget(self.register_widget)
        elif view_name == "forgot_password":
            self.stacked_widget.setCurrentWidget(self.forgot_password_widget)
        elif view_name == "reset_password":
            self.stacked_widget.setCurrentWidget(self.reset_password_widget)
        elif view_name == "verification":
            self.stacked_widget.setCurrentWidget(self.verification_widget)
        
        # Resize dialog to fit the new view's natural content height
        QTimer.singleShot(0, lambda: (self.adjustSize(), self.center_on_screen()))
    
    def update_password_strength(self):
        """Update password strength indicator."""
        password = self.register_password_edit.text()
        
        if not password:
            self.password_strength_label.setText("")
            return
        
        if len(password) < 8:
            self.password_strength_label.setText("❌ Password must be at least 8 characters")
            self.password_strength_label.setStyleSheet("color: #e05555; font-size: 13px;")
        else:
            self.password_strength_label.setText("✅ Strong password")
            self.password_strength_label.setStyleSheet("color: #4caf50; font-size: 13px;")
    
    def handle_login(self):
        """Handle login."""
        email = self.login_email_edit.text().strip().lower()
        password = self.login_password_edit.text()
        
        if not email or not password:
            self.show_message("Error", "Please enter both email and password", QMessageBox.Warning)
            return
        
        self.show_loading("Signing in...")
        QTimer.singleShot(100, lambda: self._do_login(email, password))
    
    def _do_login(self, email, password):
        """Perform login with terms compliance check."""
        print(f"[LOGIN] _do_login called for: {email}")
        success, user_profile, message, _ = self.api_client.login(email, password)
        print(f"[LOGIN] api_client.login result: success={success}, message={message}, profile={user_profile}")

        if success:
            print("[LOGIN] Login succeeded — calling accept_terms...")
            terms_ok, terms_msg = self.api_client.accept_terms()
            print(f"[LOGIN] accept_terms result: ok={terms_ok}, msg={terms_msg}")

            self.hide_loading()
            self.current_user_email = email
            # Use empty dict as fallback if profile fetch failed
            self.current_user_profile = user_profile or {"email": email}

            print("[LOGIN] Emitting login_success signal...")
            self.login_success.emit(email, self.current_user_profile)
            print("[LOGIN] login_success emitted — calling self.accept()")
            self.accept()
            print("[LOGIN] self.accept() done")
        else:
            self.hide_loading()
            print(f"[LOGIN] Login failed: {message}")
            if "verify your email" in message.lower() or "verify" in message.lower():
                self.show_verification_view(email)
            else:
                self.show_message("Login Failed", message, QMessageBox.Warning)

    def show_terms_acceptance_dialog(self):
        """Show terms acceptance confirmation using the dark card design."""
        try:
            du = self._get_dialog_utils()
            result = du.exec_dark_yes_no(
                self,
                "Accept Terms & Conditions",
                "You must accept the ROBOX Terms & Conditions to continue using the platform.\n\n"
                "Do you accept the Terms & Conditions?",
                yes_text="Accept",
                no_text="Decline",
                destructive_yes=False,
                default_no=False,
            )
            return result == QMessageBox.Yes
        except Exception:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Accept Terms & Conditions")
            msg.setText("You must accept the Terms & Conditions to continue.\n\nDo you accept?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            result = msg.exec_()
            return result == QMessageBox.Yes

    def handle_register(self):
        """Handle registration."""
        full_name = self.register_name_edit.text().strip()
        email = self.register_email_edit.text().strip().lower()
        college = self.register_college_edit.text().strip()
        password = self.register_password_edit.text()
        confirm_password = self.register_confirm_edit.text()
        
        if not all([full_name, email, college, password, confirm_password]):
            self.show_message("Error", "Please fill in all fields", QMessageBox.Warning)
            return
        
        if not self._is_valid_email(email):
            self.show_message("Error", "Please enter a valid email address", QMessageBox.Warning)
            return

        if len(password) < 8:
            self.show_message("Error", "Password must be at least 8 characters long", QMessageBox.Warning)
            return

        if password != confirm_password:
            self.show_message("Error", "Passwords do not match", QMessageBox.Warning)
            return
        
        self.show_loading("Creating account...")
        QTimer.singleShot(100, lambda: self._do_register(email, password, full_name, college))
    
    def _do_register(self, email, password, full_name, college):
        """Perform registration in background."""
        mobile = self.register_mobile_edit.text().strip()
        success, message = self.api_client.register(email, password, full_name, college, mobile)
        
        self.hide_loading()
        
        if success:
            self.show_message("Success", message, QMessageBox.Information)
            self.show_verification_view(email)
        else:
            self.show_message("Registration Failed", message, QMessageBox.Critical)
    
    def handle_forgot_password(self):
        """Handle forgot password."""
        email = self.forgot_email_edit.text().strip().lower()
        
        if not email:
            self.show_message("Error", "Please enter your email address", QMessageBox.Warning)
            return
        if not self._is_valid_email(email):
            self.show_message("Error", "Please enter a valid email address", QMessageBox.Warning)
            return
        
        self.show_loading("Sending reset code...")
        QTimer.singleShot(100, lambda: self._do_forgot_password(email))
    
    def _do_forgot_password(self, email):
        """Perform forgot password in background."""
        success, message = self.api_client.request_password_reset(email)
        
        self.hide_loading()
        
        if success:
            self._reset_email = email  # store for use in reset_password step
            self.show_message("Email Sent", "A reset code has been sent to your email address. Please check your inbox.", QMessageBox.Information)
            self.switch_view("reset_password")
        else:
            self.show_message("Reset Failed", message, QMessageBox.Critical)
    
    def handle_reset_password(self):
        """Handle password reset using the code."""
        reset_code = self.reset_code_edit.text().strip()
        new_password = self.reset_password_edit.text()
        confirm_password = self.reset_confirm_edit.text()
        
        if not reset_code:
            self.show_message("Error", "Please enter the reset code", QMessageBox.Warning)
            return
        
        if not new_password or not confirm_password:
            self.show_message("Error", "Please enter and confirm your new password", QMessageBox.Warning)
            return
        
        if new_password != confirm_password:
            self.show_message("Error", "Passwords do not match", QMessageBox.Warning)
            return
        
        self.show_loading("Updating password...")
        QTimer.singleShot(100, lambda: self._do_reset_password(reset_code, new_password))
    
    def _do_reset_password(self, token, new_password):
        """Perform password reset in background."""
        email = getattr(self, '_reset_email', self.forgot_email_edit.text().strip().lower())
        success, message = self.api_client.reset_password(email, token, new_password)
        
        self.hide_loading()
        
        if success:
            self.show_message("Success", "Password reset successfully! You can now sign in with your new password.", QMessageBox.Information)
            self.switch_view("login")
            self.reset_code_edit.clear()
            self.reset_password_edit.clear()
            self.reset_confirm_edit.clear()
        else:
            self.show_message("Reset Failed", message, QMessageBox.Critical)
    
    def _do_verify_email(self, token):
        """Perform email verification. Terms will be accepted at first login."""
        email = getattr(self, 'verification_email', '')
        success, message = self.api_client.verify_email(email, token)
        
        self.hide_loading()
        
        if success:
            self.show_message("Success", 
                            "Email verified successfully! You can now sign in. "
                            "You will be asked to accept terms and conditions on your first login.", 
                            QMessageBox.Information)
            self.switch_view("login")
        else:
            self.show_message("Verification Failed", message, QMessageBox.Critical)
    
    def show_verification_view(self, email):
        """Show verification view with clear instructions and store email for terms recording."""
        self.verification_email = email
        
        self.verification_message.setText(
            f"We've sent a verification code and Terms & Conditions to {email}. "
            "Please check your inbox, review the attached terms document, and enter the verification code below to activate your account."
        )
        self.verification_code_edit.setPlaceholderText("Enter the verification code from your email")
        if hasattr(self, 'resend_status_label'):
            self.resend_status_label.setText("")
        if hasattr(self, 'resend_verification_button'):
            self.resend_verification_button.setEnabled(True)
        self.switch_view("verification")

    def handle_resend_verification(self):
        """Trigger backend to resend verification email."""
        email = getattr(self, 'verification_email', None)
        if not email:
            self.show_message("Error", "No email available to resend verification.", QMessageBox.Warning)
            return

        if hasattr(self, 'resend_verification_button'):
            self.resend_verification_button.setEnabled(False)

        self.show_loading("Sending verification email...")
        QTimer.singleShot(100, lambda: self._do_resend_verification(email))

    def _do_resend_verification(self, email: str):
        success, message = self.api_client.resend_verification(email)
        self.hide_loading()

        if hasattr(self, 'resend_verification_button'):
            self.resend_verification_button.setEnabled(True)

        if hasattr(self, 'resend_status_label'):
            self.resend_status_label.setStyleSheet("color: #28a745;" if success else "color: #dc3545;")
            self.resend_status_label.setText(message if success else f"Failed to resend: {message}")

        if not success:
            self.show_message("Resend Failed", message, QMessageBox.Warning)

    def show_loading(self, message):
        """Show a full-screen semi-transparent overlay with a centred card."""
        if not hasattr(self, '_load_overlay'):
            overlay = QWidget(self)
            overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            overlay.setStyleSheet("background-color: rgba(0,0,0,0);")

            outer = QVBoxLayout(overlay)
            outer.setAlignment(Qt.AlignCenter)
            outer.setContentsMargins(0, 0, 0, 0)

            card = QFrame(overlay)
            card.setStyleSheet("""
                QFrame {
                    background-color: #161616;
                    border: 1px solid #2e2e2e;
                    border-radius: 16px;
                }
            """)
            card.setFixedWidth(320)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(28, 24, 28, 24)
            card_layout.setSpacing(12)
            card_layout.setAlignment(Qt.AlignCenter)

            icon_lbl = QLabel("⟳")
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet("color:#888888; font-size:32px; background:transparent; border:none;")

            self._load_text = QLabel()
            self._load_text.setAlignment(Qt.AlignCenter)
            self._load_text.setWordWrap(True)
            self._load_text.setStyleSheet(
                "color:#cccccc; font-size:15px; font-weight:600;"
                "font-family:'Segoe UI',Arial; background:transparent; border:none;"
            )

            card_layout.addWidget(icon_lbl)
            card_layout.addWidget(self._load_text)
            outer.addWidget(card)

            self._load_overlay = overlay

        self._load_text.setText(message)
        self._load_overlay.resize(self.size())
        self._load_overlay.setStyleSheet("background-color: rgba(0,0,0,180);")
        self._load_overlay.show()
        self._load_overlay.raise_()
        QApplication.processEvents()

    def hide_loading(self):
        """Hide loading overlay."""
        if hasattr(self, '_load_overlay'):
            self._load_overlay.hide()

    def _get_dialog_utils(self):
        """Lazy-import dialog_utils to avoid circular imports."""
        import importlib, sys, os
        gui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Kinematics", "gui")
        if gui_path not in sys.path:
            sys.path.insert(0, gui_path)
        return importlib.import_module("dialog_utils")

    def show_message(self, title, message, icon_type):
        """Route to the appropriate dialog_utils card based on icon type."""
        try:
            du = self._get_dialog_utils()
            if icon_type == QMessageBox.Critical:
                du.exec_dark_information(self, title, message, variant="error")
            elif icon_type == QMessageBox.Warning:
                du.exec_dark_information(self, title, message, variant="warning")
            else:
                du.exec_dark_information(self, title, message, variant="success")
        except Exception:
            msg_box = QMessageBox(self)
            msg_box.setIcon(icon_type)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.exec_()
    
    def center_on_screen(self):
        """Center dialog on screen."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def apply_styling(self):
        """Apply modern dark theme — refined typography, consistent sizing, clean structure."""
        self.setStyleSheet("""
            QDialog {
                background-color: #0d0d0d;
                color: #ffffff;
                font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
            }
            QWidget { background-color: transparent; color: #ffffff; }
            QStackedWidget { background-color: transparent; border: none; }

            /* ── Scrollbar ── */
            QScrollArea { background-color: transparent; border: none; }
            QScrollBar:vertical {
                background-color: #161616;
                width: 5px;
                border-radius: 3px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #3a3a3a;
                border-radius: 3px;
                min-height: 28px;
            }
            QScrollBar::handle:vertical:hover { background-color: #606060; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

            /* ── Page headings ── */
            QLabel#title {
                color: #ffffff;
                font-size: 36px;
                font-weight: bold;
                letter-spacing: -0.5px;
                background-color: transparent;
                padding: 0;
                margin: 0;
            }
            QLabel#subtitle {
                color: #6b6b6b;
                font-size: 16px;
                font-weight: 400;
                background-color: transparent;
                padding: 0;
                margin: 0;
            }

            /* ── Form card ── */
            QFrame { background-color: transparent; border: none; }
            QFrame#form {
                background-color: #111111;
                border: 1px solid #242424;
                border-radius: 16px;
            }

            /* ── Field labels ── */
            QLabel#field_label {
                color: #888888;
                font-size: 18px;
                font-weight: 600;
                background-color: transparent;
                padding: 0;
                margin: 8px 0 10px 0;
            }
            QLabel#small_text {
                color: #4a4a4a;
                font-size: 14px;
                background-color: transparent;
            }

            /* ── Input fields ── */
            QLineEdit#input_field {
                background-color: #1a1a1a;
                color: #f0f0f0;
                border: 1.5px solid #2e2e2e;
                border-radius: 10px;
                padding: 13px 16px;
                font-size: 16px;
                font-weight: 400;
                selection-background-color: #4a4a4a;
                min-height: 22px;
            }
            QLineEdit#input_field:focus {
                border: 1.5px solid #777777;
                background-color: #202020;
                color: #ffffff;
            }
            QLineEdit#input_field::placeholder { color: #3d3d3d; }

            /* ── Primary button ── */
            QPushButton#primary_button {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #3e3e3e;
                border-bottom: 2px solid #505050;
                border-radius: 10px;
                padding: 14px 24px;
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 0.4px;
                min-height: 24px;
            }
            QPushButton#primary_button:hover {
                background-color: #363636;
                border: 1px solid #606060;
                border-bottom: 2px solid #808080;
            }
            QPushButton#primary_button:pressed {
                background-color: #1e1e1e;
                border: 1px solid #2a2a2a;
                border-bottom: 1px solid #2a2a2a;
                padding-top: 15px;
                padding-bottom: 13px;
            }

            /* ── Link / secondary button ── */
            QPushButton#link_button {
                background-color: transparent;
                color: #666666;
                border: none;
                padding: 8px 12px;
                font-size: 15px;
                font-weight: 500;
                border-radius: 6px;
                min-height: 24px;
            }
            QPushButton#link_button:hover {
                color: #dddddd;
                background-color: rgba(255, 255, 255, 0.05);
            }
            QPushButton#link_button:pressed {
                color: #aaaaaa;
                background-color: rgba(255, 255, 255, 0.02);
            }

            /* ── Password strength ── */
            QLabel#password_strength {
                background-color: transparent;
                font-size: 13px;
                margin: 3px 0 0 0;
                padding: 0;
            }

            /* ── Terms notice card ── */
            QFrame#terms_notice {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid #202020;
                border-radius: 10px;
            }
            QLabel#terms_title {
                color: #bbbbbb;
                font-size: 15px;
                font-weight: 700;
                background-color: transparent;
            }
            QLabel#terms_text {
                color: #686868;
                font-size: 13px;
                background-color: transparent;
            }

            /* ── Checkbox ── */
            QCheckBox#terms_checkbox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 1.5px solid #2e2e2e;
                background-color: #1a1a1a;
            }
            QCheckBox#terms_checkbox::indicator:checked {
                background-color: #3c3c3c;
                border: 1.5px solid #707070;
                image: none;
            }
            QLabel#checkbox_label {
                color: #999999;
                font-size: 14px;
                background-color: transparent;
            }
        """)
