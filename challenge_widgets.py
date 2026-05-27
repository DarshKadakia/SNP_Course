"""
Challenge-specific UI components for the Robotics Bootcamp Challenge System
Provides specialized widgets for different challenge types
"""

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                           QLabel, QTableWidget, QTableWidgetItem, QLineEdit, 
                           QPushButton, QFormLayout, QSpinBox, QDoubleSpinBox,
                           QSlider, QComboBox, QCheckBox, QTabWidget,
                           QRadioButton, QButtonGroup, QGridLayout, QSplitter)
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QIcon, QTextCursor

class QuizWidget(QWidget):
    """
    Widget for quiz-type challenges
    Displays questions and allows submission of answers
    """
    
    # Signal emitted when an answer is submitted
    answer_submitted = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Quiz title and description
        self.title_label = QLabel("Quiz Challenge")
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        main_layout.addWidget(self.title_label)
        
        self.description_label = QLabel("Answer the questions to complete the challenge.")
        self.description_label.setStyleSheet("font-size: 12pt;")
        main_layout.addWidget(self.description_label)
        
        # Create a line to separate header from content
        line = QWidget()
        line.setFixedHeight(2)
        line.setSizePolicy(line.sizePolicy().Expanding, line.sizePolicy().Fixed)
        line.setStyleSheet("background-color: #cccccc;")
        main_layout.addWidget(line)
        
        # Current question display
        question_group = QGroupBox("Current Question")
        question_layout = QVBoxLayout()
        
        self.question_number_label = QLabel("Question 1 of 5")
        self.question_number_label.setStyleSheet("font-weight: bold;")
        question_layout.addWidget(self.question_number_label)
        
        self.question_text = QLabel("Question text will appear here")
        self.question_text.setWordWrap(True)
        self.question_text.setStyleSheet("font-size: 14pt; margin: 10px 0;")
        question_layout.addWidget(self.question_text)
        
        # Content widget for different question types
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        question_layout.addWidget(self.content_widget)
        
        # Answer input section
        self.answer_widget = QWidget()
        self.answer_layout = QFormLayout(self.answer_widget)
        question_layout.addWidget(self.answer_widget)
        
        # Navigation buttons
        button_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.go_to_previous)
        self.prev_button.setEnabled(False)
        
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.go_to_next)
        
        self.submit_button = QPushButton("Submit Answer")
        self.submit_button.clicked.connect(self.submit_answer)
        
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.next_button)
        button_layout.addStretch()
        button_layout.addWidget(self.submit_button)
        
        question_layout.addLayout(button_layout)
        question_group.setLayout(question_layout)
        main_layout.addWidget(question_group)
        
        # Progress section
        progress_group = QGroupBox("Quiz Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_table = QTableWidget(0, 3)
        self.progress_table.setHorizontalHeaderLabels(["Question", "Status", "Score"])
        self.progress_table.horizontalHeader().setStretchLastSection(True)
        self.progress_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.progress_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.progress_table.cellClicked.connect(self.on_question_selected)
        
        progress_layout.addWidget(self.progress_table)
        progress_group.setLayout(progress_layout)
        
        main_layout.addWidget(progress_group)
        
        # Initialize quiz data
        self.questions = []
        self.current_question_index = 0
        self.answers = {}
        self.feedback = {}
    
    def set_quiz_data(self, quiz_data):
        """
        Set quiz data and initialize the widget
        
        Parameters:
        -----------
        quiz_data : dict
            Dictionary containing quiz data:
            - 'title': Quiz title
            - 'description': Quiz description
            - 'questions': List of question dictionaries
        """
        if not quiz_data or 'questions' not in quiz_data:
            return
            
        # Set title and description
        if 'title' in quiz_data:
            self.title_label.setText(quiz_data['title'])
            
        if 'description' in quiz_data:
            self.description_label.setText(quiz_data['description'])
        
        # Store questions
        self.questions = quiz_data['questions']
        self.current_question_index = 0
        self.answers = {}
        self.feedback = {}
        
        # Setup progress table
        self.setup_progress_table()
        
        # Display first question
        self.display_current_question()
    
    def setup_progress_table(self):
        """Setup the progress table with all questions"""
        self.progress_table.setRowCount(len(self.questions))
        
        for i, question in enumerate(self.questions):
            # Question number
            item = QTableWidgetItem(f"Question {i+1}")
            self.progress_table.setItem(i, 0, item)
            
            # Status (unanswered)
            status_item = QTableWidgetItem("Unanswered")
            status_item.setForeground(QColor(128, 128, 128))
            self.progress_table.setItem(i, 1, status_item)
            
            # Score (empty)
            score_item = QTableWidgetItem("")
            self.progress_table.setItem(i, 2, score_item)
    
    def display_current_question(self):
        """Display the current question"""
        if not self.questions or self.current_question_index >= len(self.questions):
            return
            
        # Get current question
        question = self.questions[self.current_question_index]
        
        # Update question number label
        self.question_number_label.setText(f"Question {self.current_question_index + 1} of {len(self.questions)}")
        
        # Update question text
        self.question_text.setText(question.get('text', 'No question text provided'))
        
        # Clear previous content and answer widgets
        self._clear_widgets()
        
        # Create content based on question type
        question_type = question.get('type', 'text')
        
        if question_type == 'matrix':
            self._create_matrix_question(question)
        elif question_type == 'multiple_choice':
            self._create_multiple_choice_question(question)
        elif question_type == 'numeric':
            self._create_numeric_question(question)
        elif question_type == 'vector':
            self._create_vector_question(question)
        else:  # default to text
            self._create_text_question(question)
        
        # Update button states
        self.prev_button.setEnabled(self.current_question_index > 0)
        self.next_button.setEnabled(self.current_question_index < len(self.questions) - 1)
        
        # Show existing answer if available
        if self.current_question_index in self.answers:
            self._show_existing_answer()
        
        # Show feedback if available
        if self.current_question_index in self.feedback:
            self._show_feedback()
    
    def _clear_widgets(self):
        """Clear content and answer widgets"""
        # Clear content layout
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear answer layout
        while self.answer_layout.count():
            item = self.answer_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _create_matrix_question(self, question):
        """Create UI for matrix question"""
        # Add matrix visualization if provided
        if 'matrix' in question:
            matrix = question['matrix']
            
            # Create table for matrix display
            rows = len(matrix)
            cols = len(matrix[0]) if rows > 0 else 0
            
            matrix_table = QTableWidget(rows, cols)
            matrix_table.setEditTriggers(QTableWidget.NoEditTriggers)
            matrix_table.horizontalHeader().setVisible(False)
            matrix_table.verticalHeader().setVisible(False)
            
            # Fill matrix values
            for i in range(rows):
                for j in range(cols):
                    item = QTableWidgetItem(f"{matrix[i][j]:.4f}")
                    item.setTextAlignment(Qt.AlignCenter)
                    matrix_table.setItem(i, j, item)
            
            # Set equal column widths
            for i in range(cols):
                matrix_table.setColumnWidth(i, 80)
            
            self.content_layout.addWidget(QLabel("Matrix:"))
            self.content_layout.addWidget(matrix_table)
        
        # Create answer fields for axis and angle
        self.answer_layout.addRow(QLabel("Rotation Axis (x, y, z):"), QWidget())
        
        axis_layout = QHBoxLayout()
        self.axis_x = QLineEdit()
        self.axis_y = QLineEdit()
        self.axis_z = QLineEdit()
        
        axis_layout.addWidget(QLabel("x:"))
        axis_layout.addWidget(self.axis_x)
        axis_layout.addWidget(QLabel("y:"))
        axis_layout.addWidget(self.axis_y)
        axis_layout.addWidget(QLabel("z:"))
        axis_layout.addWidget(self.axis_z)
        
        axis_widget = QWidget()
        axis_widget.setLayout(axis_layout)
        self.answer_layout.addRow("", axis_widget)
        
        self.angle_input = QLineEdit()
        self.answer_layout.addRow("Rotation Angle (radians):", self.angle_input)
    
    def _create_multiple_choice_question(self, question):
        """Create UI for multiple choice question"""
        if 'choices' in question:
            choices = question['choices']
            
            # Create radio buttons for choices
            self.choice_group = QButtonGroup(self)
            
            for i, choice in enumerate(choices):
                radio = QRadioButton(choice)
                self.choice_group.addButton(radio, i)
                self.content_layout.addWidget(radio)
    
    def _create_numeric_question(self, question):
        """Create UI for numeric question"""
        self.numeric_input = QLineEdit()
        if 'unit' in question:
            self.answer_layout.addRow(f"Answer ({question['unit']}):", self.numeric_input)
        else:
            self.answer_layout.addRow("Answer:", self.numeric_input)
    
    def _create_vector_question(self, question):
        """Create UI for vector question"""
        vector_layout = QHBoxLayout()
        
        self.vector_inputs = []
        dimension = question.get('dimension', 3)
        
        for i in range(dimension):
            vector_input = QLineEdit()
            self.vector_inputs.append(vector_input)
            
            vector_layout.addWidget(QLabel(f"{chr(120+i)}:"))  # x, y, z, ...
            vector_layout.addWidget(vector_input)
        
        vector_widget = QWidget()
        vector_widget.setLayout(vector_layout)
        
        self.answer_layout.addRow("Vector:", vector_widget)
    
    def _create_text_question(self, question):
        """Create UI for text question"""
        self.text_input = QLineEdit()
        self.answer_layout.addRow("Answer:", self.text_input)
    
    def _show_existing_answer(self):
        """Show existing answer for the current question"""
        answer = self.answers[self.current_question_index]
        question = self.questions[self.current_question_index]
        question_type = question.get('type', 'text')
        
        if question_type == 'matrix':
            if isinstance(answer, dict) and 'axis' in answer and 'angle' in answer:
                axis = answer['axis']
                if len(axis) >= 3:
                    self.axis_x.setText(str(axis[0]))
                    self.axis_y.setText(str(axis[1]))
                    self.axis_z.setText(str(axis[2]))
                
                self.angle_input.setText(str(answer['angle']))
                
        elif question_type == 'multiple_choice':
            if isinstance(answer, int) and 0 <= answer < self.choice_group.buttons():
                self.choice_group.button(answer).setChecked(True)
                
        elif question_type == 'numeric':
            self.numeric_input.setText(str(answer))
            
        elif question_type == 'vector':
            if isinstance(answer, list):
                for i, value in enumerate(answer):
                    if i < len(self.vector_inputs):
                        self.vector_inputs[i].setText(str(value))
                        
        else:  # text
            self.text_input.setText(str(answer))
    
    def _show_feedback(self):
        """Show feedback for the current question"""
        feedback = self.feedback[self.current_question_index]
        
        # Create feedback widget if not exists
        if not hasattr(self, 'feedback_label'):
            self.feedback_label = QLabel()
            self.feedback_label.setWordWrap(True)
            self.feedback_label.setStyleSheet("""
                padding: 10px;
                border-radius: 5px;
                background-color: #f0f0f0;
                font-weight: bold;
            """)
            self.content_layout.addWidget(self.feedback_label)
        
        # Update feedback text and style
        if 'correct' in feedback:
            is_correct = feedback['correct']
            score = feedback.get('score', 0)
            
            if is_correct:
                self.feedback_label.setText(f"Correct! Score: {score}/100")
                self.feedback_label.setStyleSheet("""
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #dff0d8;
                    color: #3c763d;
                    font-weight: bold;
                """)
            else:
                self.feedback_label.setText(f"Incorrect. Score: {score}/100")
                self.feedback_label.setStyleSheet("""
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #f2dede;
                    color: #a94442;
                    font-weight: bold;
                """)
        
        # Update progress table
        self._update_progress_table()
    
    def _update_progress_table(self):
        """Update progress table with current status"""
        for i in range(len(self.questions)):
            # Status
            status_item = self.progress_table.item(i, 1)
            if i in self.answers:
                if i in self.feedback and 'correct' in self.feedback[i]:
                    if self.feedback[i]['correct']:
                        status_item.setText("Correct")
                        status_item.setForeground(QColor(60, 118, 61))  # Green
                    else:
                        status_item.setText("Incorrect")
                        status_item.setForeground(QColor(169, 68, 66))  # Red
                else:
                    status_item.setText("Answered")
                    status_item.setForeground(QColor(49, 112, 143))  # Blue
            else:
                status_item.setText("Unanswered")
                status_item.setForeground(QColor(128, 128, 128))  # Gray
            
            # Score
            score_item = self.progress_table.item(i, 2)
            if i in self.feedback and 'score' in self.feedback[i]:
                score_item.setText(f"{self.feedback[i]['score']}/100")
            else:
                score_item.setText("")
    
    def go_to_previous(self):
        """Go to previous question"""
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.display_current_question()
    
    def go_to_next(self):
        """Go to next question"""
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            self.display_current_question()
    
    def on_question_selected(self, row, column):
        """Handle question selection in progress table"""
        if 0 <= row < len(self.questions):
            self.current_question_index = row
            self.display_current_question()
    
    def submit_answer(self):
        """Submit answer for current question"""
        if not self.questions or self.current_question_index >= len(self.questions):
            return
            
        question = self.questions[self.current_question_index]
        question_type = question.get('type', 'text')
        
        # Extract answer based on question type
        answer = None
        
        if question_type == 'matrix':
            try:
                x = float(self.axis_x.text())
                y = float(self.axis_y.text())
                z = float(self.axis_z.text())
                angle = float(self.angle_input.text())
                
                # Normalize axis
                norm = np.sqrt(x*x + y*y + z*z)
                if norm > 0:
                    x /= norm
                    y /= norm
                    z /= norm
                
                answer = {
                    'axis': [x, y, z],
                    'angle': angle
                }
            except ValueError:
                # Invalid input
                return
                
        elif question_type == 'multiple_choice':
            answer = self.choice_group.checkedId()
            if answer < 0:  # No selection
                return
                
        elif question_type == 'numeric':
            try:
                answer = float(self.numeric_input.text())
            except ValueError:
                # Invalid input
                return
                
        elif question_type == 'vector':
            try:
                answer = []
                for input_field in self.vector_inputs:
                    answer.append(float(input_field.text()))
            except ValueError:
                # Invalid input
                return
                
        else:  # text
            answer = self.text_input.text()
            if not answer.strip():  # Empty answer
                return
        
        # Store answer
        self.answers[self.current_question_index] = answer
        
        # Emit signal with question index and answer
        self.answer_submitted.emit({
            'question_index': self.current_question_index,
            'answer': answer,
            'question_type': question_type
        })
        
        # Move to next question if available
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            self.display_current_question()
    
    def set_feedback(self, question_index, feedback):
        """
        Set feedback for a question
        
        Parameters:
        -----------
        question_index : int
            Index of the question
        feedback : dict
            Feedback dictionary with keys:
            - 'correct': Boolean indicating whether the answer is correct
            - 'score': Numeric score for the answer
            - 'message': Optional feedback message
        """
        if 0 <= question_index < len(self.questions):
            self.feedback[question_index] = feedback
            
            # Update display if current question
            if question_index == self.current_question_index:
                self._show_feedback()
            
            # Update progress table
            self._update_progress_table()
    
    def get_quiz_results(self):
        """
        Get overall quiz results
        
        Returns:
        --------
        dict
            Dictionary with quiz results:
            - 'total_score': Total score for all questions
            - 'max_score': Maximum possible score
            - 'percentage': Percentage score
            - 'questions_answered': Number of questions answered
            - 'questions_correct': Number of questions answered correctly
        """
        total_score = 0
        questions_answered = len(self.answers)
        questions_correct = 0
        
        for i in range(len(self.questions)):
            if i in self.feedback and 'score' in self.feedback[i]:
                total_score += self.feedback[i]['score']
                if self.feedback[i].get('correct', False):
                    questions_correct += 1
        
        max_score = 100 * len(self.questions)
        percentage = (total_score / max_score) * 100 if max_score > 0 else 0
        
        return {
            'total_score': total_score,
            'max_score': max_score,
            'percentage': percentage,
            'questions_answered': questions_answered,
            'questions_correct': questions_correct,
            'total_questions': len(self.questions)
        }


class OrientationWidget(QWidget):
    """
    Widget for orientation-related challenges
    Visualizes robot orientation and allows user to input orientation data
    """
    
    # Signal emitted when orientation is submitted
    orientation_submitted = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create visualization and input areas
        splitter = QSplitter(Qt.Vertical)
        
        # Visualization area
        viz_widget = QWidget()
        viz_layout = QVBoxLayout(viz_widget)
        
        # Create 3D plot for orientation visualization
        self.orientation_plot = pg.PlotWidget()
        self.orientation_plot.setBackground('w')
        self.orientation_plot.setTitle("End-Effector Orientation", color="k")
        self.orientation_plot.setLabel("left", "Z", color="k")
        self.orientation_plot.setLabel("bottom", "X", color="k")
        self.orientation_plot.showGrid(x=True, y=True)
        
        # Create arrows for coordinate frames
        self.current_frame = {
            'origin': pg.ScatterPlotItem(pos=[[0, 0]], symbol='o', size=10, brush='w', pen='k'),
            'x': pg.ArrowItem(angle=0, headLen=20, headWidth=10, tailLen=80, pen=pg.mkPen('r', width=2), brush='r'),
            'y': pg.ArrowItem(angle=90, headLen=20, headWidth=10, tailLen=80, pen=pg.mkPen('g', width=2), brush='g'),
            'z': pg.ArrowItem(angle=180, headLen=20, headWidth=10, tailLen=80, pen=pg.mkPen('b', width=2), brush='b')
        }
        
        self.target_frame = {
            'origin': pg.ScatterPlotItem(pos=[[0, 0]], symbol='o', size=10, brush='y', pen='k'),
            'x': pg.ArrowItem(angle=0, headLen=20, headWidth=10, tailLen=80, pen=pg.mkPen('r', width=2, style=Qt.DashLine), brush='r'),
            'y': pg.ArrowItem(angle=90, headLen=20, headWidth=10, tailLen=80, pen=pg.mkPen('g', width=2, style=Qt.DashLine), brush='g'),
            'z': pg.ArrowItem(angle=180, headLen=20, headWidth=10, tailLen=80, pen=pg.mkPen('b', width=2, style=Qt.DashLine), brush='b')
        }
        
        # Add items to plot
        for item in self.current_frame.values():
            self.orientation_plot.addItem(item)
        
        for item in self.target_frame.values():
            self.orientation_plot.addItem(item)
            item.setVisible(False)  # Hide target frame initially
        
        viz_layout.addWidget(self.orientation_plot)
        
        # Error display
        error_layout = QHBoxLayout()
        
        self.error_label = QLabel("Orientation Error: N/A")
        self.error_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        error_layout.addWidget(self.error_label)
        
        viz_layout.addLayout(error_layout)
        
        # Input area
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        # Rotation matrix input
        matrix_group = QGroupBox("Rotation Matrix Input")
        matrix_layout = QGridLayout()
        
        self.matrix_inputs = []
        for i in range(3):
            row = []
            for j in range(3):
                matrix_input = QLineEdit()
                matrix_input.setFixedWidth(80)
                matrix_layout.addWidget(matrix_input, i, j)
                row.append(matrix_input)
            self.matrix_inputs.append(row)
        
        # Add buttons for matrix input
        button_layout = QHBoxLayout()
        
        identity_button = QPushButton("Identity")
        identity_button.clicked.connect(self.set_identity_matrix)
        button_layout.addWidget(identity_button)
        
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_matrix)
        button_layout.addWidget(clear_button)
        
        verify_button = QPushButton("Verify Matrix")
        verify_button.clicked.connect(self.verify_matrix)
        button_layout.addWidget(verify_button)
        
        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.submit_orientation)
        button_layout.addWidget(submit_button)
        
        matrix_layout.addLayout(button_layout, 3, 0, 1, 3)
        matrix_group.setLayout(matrix_layout)
        input_layout.addWidget(matrix_group)
        
        # Alternative input methods
        alt_input_group = QGroupBox("Alternative Input Methods")
        alt_layout = QVBoxLayout()
        
        # Euler angles input
        euler_layout = QHBoxLayout()
        euler_layout.addWidget(QLabel("Euler Angles (rad):"))
        
        self.euler_inputs = []
        euler_labels = ["Roll:", "Pitch:", "Yaw:"]
        
        for i, label in enumerate(euler_labels):
            input_layout = QHBoxLayout()
            input_layout.addWidget(QLabel(label))
            
            euler_input = QDoubleSpinBox()
            euler_input.setRange(-np.pi, np.pi)
            euler_input.setSingleStep(0.1)
            euler_input.setDecimals(3)
            euler_input.valueChanged.connect(self.on_euler_changed)
            
            self.euler_inputs.append(euler_input)
            input_layout.addWidget(euler_input)
            
            euler_layout.addLayout(input_layout)
        
        euler_layout.addWidget(QPushButton("Update Matrix"))  # Will be connected later
        
        alt_layout.addLayout(euler_layout)
        
        # Axis-angle input
        axis_layout = QHBoxLayout()
        axis_layout.addWidget(QLabel("Axis-Angle:"))
        
        # Axis inputs
        axis_widget = QWidget()
        axis_input_layout = QHBoxLayout(axis_widget)
        
        self.axis_inputs = []
        axis_labels = ["X:", "Y:", "Z:"]
        
        for i, label in enumerate(axis_labels):
            axis_input_layout.addWidget(QLabel(label))
            
            axis_input = QDoubleSpinBox()
            axis_input.setRange(-1, 1)
            axis_input.setSingleStep(0.1)
            axis_input.setDecimals(3)
            
            self.axis_inputs.append(axis_input)
            axis_input_layout.addWidget(axis_input)
        
        axis_layout.addWidget(axis_widget)
        
        # Angle input
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle (rad):"))
        
        self.angle_input = QDoubleSpinBox()
        self.angle_input.setRange(-np.pi, np.pi)
        self.angle_input.setSingleStep(0.1)
        self.angle_input.setDecimals(3)
        
        angle_layout.addWidget(self.angle_input)
        angle_layout.addWidget(QPushButton("Update Matrix"))  # Will be connected later
        
        axis_layout.addLayout(angle_layout)
        alt_layout.addLayout(axis_layout)
        
        alt_input_group.setLayout(alt_layout)
        input_layout.addWidget(alt_input_group)
        
        # Add widgets to splitter
        splitter.addWidget(viz_widget)
        splitter.addWidget(input_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([600, 400])
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Initialize data
        self.current_orientation = np.eye(3)
        self.target_orientation = None
        self.update_visualization()
    
    def update_visualization(self):
        """Update orientation visualization based on current data"""
        # Update current frame
        self._update_frame(self.current_orientation, self.current_frame)
        
        # Update target frame if available
        if self.target_orientation is not None:
            self._update_frame(self.target_orientation, self.target_frame)
            for item in self.target_frame.values():
                item.setVisible(True)
            
            # Calculate orientation error
            error = self.calculate_orientation_error()
            self.error_label.setText(f"Orientation Error: {error:.4f} rad")
        else:
            # Hide target frame if no target orientation
            for item in self.target_frame.values():
                item.setVisible(False)
            self.error_label.setText("Orientation Error: N/A")
    
    def _update_frame(self, rotation_matrix, frame_items):
        """Update frame visualization with rotation matrix"""
        # Origin at center
        origin = [0, 0]
        
        # Scale for better visualization
        scale = 1.0
        
        # Calculate unit vectors in rotated frame
        x_axis = scale * rotation_matrix[:2, 0]  # First column for X
        y_axis = scale * rotation_matrix[:2, 1]  # Second column for Y
        z_axis = scale * rotation_matrix[:2, 2]  # Third column for Z
        
        # Update arrows
        frame_items['x'].setPos(origin[0], origin[1])
        frame_items['x'].setStyle(angle=np.degrees(np.arctan2(x_axis[1], x_axis[0])))
        
        frame_items['y'].setPos(origin[0], origin[1])
        frame_items['y'].setStyle(angle=np.degrees(np.arctan2(y_axis[1], y_axis[0])))
        
        frame_items['z'].setPos(origin[0], origin[1])
        frame_items['z'].setStyle(angle=np.degrees(np.arctan2(z_axis[1], z_axis[0])))
    
    def calculate_orientation_error(self):
        """Calculate error between current and target orientation"""
        if self.target_orientation is None:
            return 0.0
            
        # Calculate error using matrix difference
        # Error = ||R1 - R2||_F
        diff = self.current_orientation - self.target_orientation
        error = np.linalg.norm(diff, 'fro')
        
        return error
    
    def set_current_orientation(self, orientation_matrix):
        """Set current orientation matrix and update visualization"""
        if orientation_matrix.shape == (3, 3):
            self.current_orientation = orientation_matrix
            self.update_matrix_inputs()
            self.update_visualization()
    
    def set_target_orientation(self, orientation_matrix):
        """Set target orientation matrix and update visualization"""
        if orientation_matrix is None:
            self.target_orientation = None
        elif orientation_matrix.shape == (3, 3):
            self.target_orientation = orientation_matrix
        self.update_visualization()
    
    def update_matrix_inputs(self):
        """Update matrix input fields with current orientation"""
        for i in range(3):
            for j in range(3):
                self.matrix_inputs[i][j].setText(f"{self.current_orientation[i, j]:.4f}")
    
    def set_identity_matrix(self):
        """Set identity matrix in input fields"""
        for i in range(3):
            for j in range(3):
                if i == j:
                    self.matrix_inputs[i][j].setText("1.0000")
                else:
                    self.matrix_inputs[i][j].setText("0.0000")
    
    def clear_matrix(self):
        """Clear all matrix input fields"""
        for i in range(3):
            for j in range(3):
                self.matrix_inputs[i][j].setText("")
    
    def verify_matrix(self):
        """Verify if input matrix is a valid rotation matrix"""
        try:
            # Read matrix from input fields
            matrix = np.zeros((3, 3))
            for i in range(3):
                for j in range(3):
                    matrix[i, j] = float(self.matrix_inputs[i][j].text())
            
            # Check orthogonality
            mtm = matrix.T @ matrix
            identity = np.eye(3)
            orthogonal_error = np.linalg.norm(mtm - identity, 'fro')
            
            # Check determinant
            det = np.linalg.det(matrix)
            
            if orthogonal_error < 1e-3 and abs(det - 1.0) < 1e-3:
                # Valid rotation matrix
                self.current_orientation = matrix
                self.update_visualization()
                
                # Display success message
                message = "Valid rotation matrix ✓"
                self.error_label.setText(message)
                self.error_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                # Invalid rotation matrix
                message = "Invalid rotation matrix ✗"
                self.error_label.setText(message)
                self.error_label.setStyleSheet("color: red; font-weight: bold;")
                
        except ValueError:
            # Invalid input
            message = "Invalid input ✗"
            self.error_label.setText(message)
            self.error_label.setStyleSheet("color: red; font-weight: bold;")
    
    def submit_orientation(self):
        """Submit the current orientation matrix"""
        try:
            # Read matrix from input fields
            matrix = np.zeros((3, 3))
            for i in range(3):
                for j in range(3):
                    matrix[i, j] = float(self.matrix_inputs[i][j].text())
            
            # Verify matrix is valid
            mtm = matrix.T @ matrix
            identity = np.eye(3)
            orthogonal_error = np.linalg.norm(mtm - identity, 'fro')
            det = np.linalg.det(matrix)
            
            if orthogonal_error < 1e-3 and abs(det - 1.0) < 1e-3:
                # Valid rotation matrix
                self.current_orientation = matrix
                self.update_visualization()
                
                # Emit signal with matrix
                self.orientation_submitted.emit({
                    'orientation_matrix': matrix.tolist()
                })
            else:
                # Invalid rotation matrix
                message = "Cannot submit: Invalid rotation matrix ✗"
                self.error_label.setText(message)
                self.error_label.setStyleSheet("color: red; font-weight: bold;")
                
        except ValueError:
            # Invalid input
            message = "Cannot submit: Invalid input ✗"
            self.error_label.setText(message)
            self.error_label.setStyleSheet("color: red; font-weight: bold;")
    
    def on_euler_changed(self):
        """Handle changes to Euler angle inputs"""
        try:
            # Get Euler angles
            roll = self.euler_inputs[0].value()
            pitch = self.euler_inputs[1].value()
            yaw = self.euler_inputs[2].value()
            
            # Convert to rotation matrix
            Rx = np.array([
                [1, 0, 0],
                [0, np.cos(roll), -np.sin(roll)],
                [0, np.sin(roll), np.cos(roll)]
            ])
            
            Ry = np.array([
                [np.cos(pitch), 0, np.sin(pitch)],
                [0, 1, 0],
                [-np.sin(pitch), 0, np.cos(pitch)]
            ])
            
            Rz = np.array([
                [np.cos(yaw), -np.sin(yaw), 0],
                [np.sin(yaw), np.cos(yaw), 0],
                [0, 0, 1]
            ])
            
            # Combined rotation matrix (ZYX order)
            R = Rz @ Ry @ Rx
            
            # Update matrix inputs
            for i in range(3):
                for j in range(3):
                    self.matrix_inputs[i][j].setText(f"{R[i, j]:.4f}")
                    
            # Update visualization
            self.current_orientation = R
            self.update_visualization()
            
        except Exception as e:
            print(f"Error updating from Euler angles: {str(e)}")


class WorkspaceWidget(QWidget):
    """
    Widget for workspace-related challenges
    Visualizes robot workspace and allows testing point reachability
    """
    
    # Signal emitted when a point is classified
    point_classified = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create visualization and input areas
        splitter = QSplitter(Qt.Vertical)
        
        # Workspace visualization
        viz_widget = QWidget()
        viz_layout = QVBoxLayout(viz_widget)
        
        # Create 2D workspace plot
        self.workspace_plot = pg.PlotWidget()
        self.workspace_plot.setBackground('w')
        self.workspace_plot.setTitle("Robot Workspace", color="k")
        self.workspace_plot.setLabel("left", "Y Position (m)", color="k")
        self.workspace_plot.setLabel("bottom", "X Position (m)", color="k")
        self.workspace_plot.showGrid(x=True, y=True)
        
        # Maintain aspect ratio
        self.workspace_plot.setAspectLocked(True)
        
        # Add robot base and workspace boundary
        self.robot_base = pg.ScatterPlotItem(pos=[[0, 0]], symbol='o', size=20, brush='k', pen='w')
        self.workspace_plot.addItem(self.robot_base)
        
        # Workspace boundary (circle)
        boundary_points = []
        radius = 1.0  # Default radius
        for angle in np.linspace(0, 2*np.pi, 100):
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            boundary_points.append([x, y])
        
        self.workspace_boundary = pg.PlotDataItem(
            np.array(boundary_points), 
            pen=pg.mkPen('b', width=2, style=Qt.DashLine)
        )
        self.workspace_plot.addItem(self.workspace_boundary)
        
        # Plot items for test points
        self.test_points = pg.ScatterPlotItem(brush='y', pen='k', size=15, symbol='o')
        self.workspace_plot.addItem(self.test_points)
        
        self.reachable_points = pg.ScatterPlotItem(brush='g', pen='k', size=15, symbol='o')
        self.workspace_plot.addItem(self.reachable_points)
        
        self.unreachable_points = pg.ScatterPlotItem(brush='r', pen='k', size=15, symbol='o')
        self.workspace_plot.addItem(self.unreachable_points)
        
        # Current point indicator
        self.current_point = pg.ScatterPlotItem(brush='c', pen='k', size=20, symbol='o')
        self.workspace_plot.addItem(self.current_point)
        
        viz_layout.addWidget(self.workspace_plot)
        
        # Point classification controls
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Current point display
        point_group = QGroupBox("Current Point")
        point_layout = QVBoxLayout()
        
        self.point_index_label = QLabel("Point: 1 of 10")
        self.point_index_label.setStyleSheet("font-weight: bold;")
        point_layout.addWidget(self.point_index_label)
        
        self.point_coords_label = QLabel("Coordinates: (0.0, 0.0)")
        point_layout.addWidget(self.point_coords_label)
        
        # Reachability buttons
        button_layout = QHBoxLayout()
        
        self.reachable_button = QPushButton("Reachable")
        self.reachable_button.setStyleSheet("background-color: #5cb85c; color: white;")
        self.reachable_button.clicked.connect(lambda: self.classify_point(True))
        button_layout.addWidget(self.reachable_button)
        
        self.unreachable_button = QPushButton("Unreachable")
        self.unreachable_button.setStyleSheet("background-color: #d9534f; color: white;")
        self.unreachable_button.clicked.connect(lambda: self.classify_point(False))
        button_layout.addWidget(self.unreachable_button)
        
        point_layout.addLayout(button_layout)
        point_group.setLayout(point_layout)
        controls_layout.addWidget(point_group)
        
        # Progress display
        progress_group = QGroupBox("Challenge Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_label = QLabel("0/0 points classified")
        progress_layout.addWidget(self.progress_label)
        
        self.accuracy_label = QLabel("Accuracy: N/A")
        progress_layout.addWidget(self.accuracy_label)
        
        progress_group.setLayout(progress_layout)
        controls_layout.addWidget(progress_group)
        
        # Legend
        legend_group = QGroupBox("Legend")
        legend_layout = QHBoxLayout()
        
        legend_items = [
            ("Robot Base", "black"),
            ("Test Point", "yellow"),
            ("Reachable", "green"),
            ("Unreachable", "red"),
            ("Current Point", "cyan")
        ]
        
        for name, color in legend_items:
            item_layout = QHBoxLayout()
            
            color_box = QLabel()
            color_box.setFixedSize(16, 16)
            color_box.setStyleSheet(f"background-color: {color}; border: 1px solid black;")
            item_layout.addWidget(color_box)
            
            item_layout.addWidget(QLabel(name))
            legend_layout.addLayout(item_layout)
        
        legend_group.setLayout(legend_layout)
        controls_layout.addWidget(legend_group)
        
        # Add to splitter
        splitter.addWidget(viz_widget)
        splitter.addWidget(controls_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([700, 300])
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Initialize data
        self.test_point_data = []
        self.reachable_point_data = []
        self.unreachable_point_data = []
        self.current_point_index = 0
        self.max_radius = 1.0
    
    def set_workspace_data(self, workspace_data):
        """
        Set workspace data for visualization
        
        Parameters:
        -----------
        workspace_data : dict
            Dictionary containing workspace information:
            - 'max_radius': Maximum radius of robot reach
            - 'test_points': List of points to classify
            - 'reachable_points': Already classified reachable points
            - 'unreachable_points': Already classified unreachable points
        """
        # Update max radius if provided
        if 'max_radius' in workspace_data:
            self.max_radius = workspace_data['max_radius']
            self._update_workspace_boundary()
        
        # Set test points
        if 'test_points' in workspace_data:
            self.test_point_data = workspace_data['test_points']
            self._update_point_plots()
        
        # Set already classified points
        if 'reachable_points' in workspace_data:
            self.reachable_point_data = workspace_data['reachable_points']
            self._update_point_plots()
        
        if 'unreachable_points' in workspace_data:
            self.unreachable_point_data = workspace_data['unreachable_points']
            self._update_point_plots()
        
        # Reset current point index
        self.current_point_index = 0
        self._update_current_point()
        
        # Update progress display
        self._update_progress_display()
        
        # Auto-range plot to show all points
        self.workspace_plot.autoRange()
    
    def _update_workspace_boundary(self):
        """Update the workspace boundary visualization"""
        # Create boundary points on a circle
        boundary_points = []
        for angle in np.linspace(0, 2*np.pi, 100):
            x = self.max_radius * np.cos(angle)
            y = self.max_radius * np.sin(angle)
            boundary_points.append([x, y])
        
        self.workspace_boundary.setData(np.array(boundary_points))
    
    def _update_point_plots(self):
        """Update all point plots with current data"""
        # Test points (yellow)
        test_points = []
        for point in self.test_point_data:
            if point not in self.reachable_point_data and point not in self.unreachable_point_data:
                test_points.append(point)
        
        if test_points:
            self.test_points.setData(pos=np.array(test_points))
        else:
            self.test_points.setData(pos=np.empty((0, 2)))
        
        # Reachable points (green)
        if self.reachable_point_data:
            self.reachable_points.setData(pos=np.array(self.reachable_point_data))
        else:
            self.reachable_points.setData(pos=np.empty((0, 2)))
        
        # Unreachable points (red)
        if self.unreachable_point_data:
            self.unreachable_points.setData(pos=np.array(self.unreachable_point_data))
        else:
            self.unreachable_points.setData(pos=np.empty((0, 2)))
    
    def _update_current_point(self):
        """Update the current point indicator"""
        # Get points that remain to be classified
        remaining_points = []
        for point in self.test_point_data:
            if point not in self.reachable_point_data and point not in self.unreachable_point_data:
                remaining_points.append(point)
        
        if not remaining_points:
            # No more points to classify
            self.current_point.setData(pos=np.empty((0, 2)))
            self.point_coords_label.setText("No more points to classify")
            self.reachable_button.setEnabled(False)
            self.unreachable_button.setEnabled(False)
            return
        
        # Make sure current_point_index is within range
        self.current_point_index = min(self.current_point_index, len(remaining_points) - 1)
        
        # Update current point
        current_pos = remaining_points[self.current_point_index]
        self.current_point.setData(pos=[current_pos])
        
        # Update labels
        self.point_index_label.setText(f"Point: {self.current_point_index + 1} of {len(remaining_points)}")
        self.point_coords_label.setText(f"Coordinates: ({current_pos[0]:.2f}, {current_pos[1]:.2f})")
        
        # Enable buttons
        self.reachable_button.setEnabled(True)
        self.unreachable_button.setEnabled(True)
    
    def _update_progress_display(self):
        """Update progress display with current classification status"""
        total_points = len(self.test_point_data)
        classified_points = len(self.reachable_point_data) + len(self.unreachable_point_data)
        
        self.progress_label.setText(f"{classified_points}/{total_points} points classified")
        
        # Update accuracy if available
        if hasattr(self, 'accuracy'):
            self.accuracy_label.setText(f"Accuracy: {self.accuracy * 100:.1f}%")
        else:
            self.accuracy_label.setText("Accuracy: N/A")
    
    def classify_point(self, is_reachable):
        """
        Classify the current point as reachable or unreachable
        
        Parameters:
        -----------
        is_reachable : bool
            True if the point is reachable, False otherwise
        """
        # Get remaining points
        remaining_points = []
        for point in self.test_point_data:
            if point not in self.reachable_point_data and point not in self.unreachable_point_data:
                remaining_points.append(point)
        
        if not remaining_points:
            return
        
        # Get current point
        current_pos = remaining_points[self.current_point_index]
        
        # Add to appropriate list
        if is_reachable:
            self.reachable_point_data.append(current_pos)
        else:
            self.unreachable_point_data.append(current_pos)
        
        # Update plots
        self._update_point_plots()
        
        # Move to next point
        self.current_point_index = (self.current_point_index + 1) % len(remaining_points)
        self._update_current_point()
        
        # Update progress
        self._update_progress_display()
        
        # Emit signal with classification
        self.point_classified.emit({
            'point': current_pos,
            'is_reachable': is_reachable
        })
    
    def set_classification_feedback(self, feedback):
        """
        Set feedback on point classification accuracy
        
        Parameters:
        -----------
        feedback : dict
            Dictionary with feedback information:
            - 'accuracy': Overall classification accuracy
            - 'correct_classifications': Number of correct classifications
            - 'total_classifications': Total number of classifications
        """
        if 'accuracy' in feedback:
            self.accuracy = feedback['accuracy']
            self.accuracy_label.setText(f"Accuracy: {self.accuracy * 100:.1f}%")


class RobotControlWidget(QWidget):
    """
    Widget for direct robot control challenges
    Allows visualization and control of robot joints
    """
    
    # Signal emitted when control parameters are changed
    control_updated = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for control panels
        splitter = QSplitter(Qt.Vertical)
        
        # Robot visualization panel
        viz_panel = QGroupBox("Robot Visualization")
        viz_layout = QVBoxLayout()
        
        # Placeholder for robot visualization
        # This would typically be a 3D visualization widget
        self.robot_viz = QLabel("Robot visualization will appear here")
        self.robot_viz.setAlignment(Qt.AlignCenter)
        self.robot_viz.setMinimumHeight(300)
        self.robot_viz.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        viz_layout.addWidget(self.robot_viz)
        
        viz_panel.setLayout(viz_layout)
        
        # Joint control panel
        control_panel = QGroupBox("Joint Control")
        control_layout = QVBoxLayout()
        
        self.joint_sliders = []
        self.joint_readouts = []
        self.joint_layouts = []
        
        # Create sliders for 6 joints
        for i in range(6):
            joint_layout = QHBoxLayout()
            
            # Joint label
            joint_label = QLabel(f"Joint {i+1}:")
            joint_label.setMinimumWidth(60)
            joint_layout.addWidget(joint_label)
            
            # Joint slider
            joint_slider = QSlider(Qt.Horizontal)
            joint_slider.setRange(-180, 180)
            joint_slider.setValue(0)
            joint_slider.setTickPosition(QSlider.TicksBelow)
            joint_slider.setTickInterval(30)
            joint_slider.valueChanged.connect(lambda value, idx=i: self.on_slider_changed(idx, value))
            joint_layout.addWidget(joint_slider)
            
            # Joint readout
            joint_readout = QLineEdit("0.00")
            joint_readout.setMaximumWidth(60)
            joint_readout.setAlignment(Qt.AlignRight)
            joint_readout.returnPressed.connect(lambda idx=i: self.on_readout_changed(idx))
            joint_layout.addWidget(joint_readout)
            
            # Angle unit
            joint_layout.addWidget(QLabel("deg"))
            
            # Store references
            self.joint_sliders.append(joint_slider)
            self.joint_readouts.append(joint_readout)
            self.joint_layouts.append(joint_layout)
            
            control_layout.addLayout(joint_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.home_button = QPushButton("Home Position")
        self.home_button.clicked.connect(self.set_home_position)
        button_layout.addWidget(self.home_button)
        
        self.zero_button = QPushButton("Zero All Joints")
        self.zero_button.clicked.connect(self.zero_joints)
        button_layout.addWidget(self.zero_button)
        
        control_layout.addLayout(button_layout)
        
        control_panel.setLayout(control_layout)
        
        # Add panels to splitter
        splitter.addWidget(viz_panel)
        splitter.addWidget(control_panel)
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
    
    def on_slider_changed(self, joint_index, value):
        """Handle joint slider value change"""
        # Update readout
        self.joint_readouts[joint_index].setText(f"{value/10:.1f}")
        
        # Emit control update signal
        self.emit_control_update()
    
    def on_readout_changed(self, joint_index):
        """Handle joint readout value change"""
        try:
            # Get value from readout
            value = float(self.joint_readouts[joint_index].text())
            
            # Clamp to slider range
            value = max(-180, min(180, value))
            
            # Update slider (which will update the readout again)
            self.joint_sliders[joint_index].setValue(int(value * 10))
            
            # Emit control update signal
            self.emit_control_update()
            
        except ValueError:
            # Invalid input, reset to slider value
            slider_value = self.joint_sliders[joint_index].value()
            self.joint_readouts[joint_index].setText(f"{slider_value/10:.1f}")
    
    def set_home_position(self):
        """Set robot to home position"""
        # Define home position joint angles
        home_angles = [0, 0, 90, 0, 0, 0]  # Example home position
        
        # Update sliders
        for i, angle in enumerate(home_angles):
            if i < len(self.joint_sliders):
                self.joint_sliders[i].setValue(int(angle * 10))
    
    def zero_joints(self):
        """Set all joints to zero"""
        for slider in self.joint_sliders:
            slider.setValue(0)
    
    def emit_control_update(self):
        """Emit signal with current joint angles"""
        joint_angles = []
        for readout in self.joint_readouts:
            try:
                angle = float(readout.text())
                joint_angles.append(angle)
            except ValueError:
                joint_angles.append(0.0)
        
        self.control_updated.emit({
            'joint_angles': joint_angles
        })
    
    def set_joint_angles(self, joint_angles):
        """
        Set joint angles in UI without triggering signals
        
        Parameters:
        -----------
        joint_angles : list
            List of joint angles in degrees
        """
        for i, angle in enumerate(joint_angles):
            if i < len(self.joint_sliders):
                # Block signals to prevent recursion
                self.joint_sliders[i].blockSignals(True)
                self.joint_sliders[i].setValue(int(angle * 10))
                self.joint_sliders[i].blockSignals(False)
                
                self.joint_readouts[i].setText(f"{angle:.1f}")