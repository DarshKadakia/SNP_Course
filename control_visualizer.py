"""
Control Visualization Module for the Robotics Bootcamp Challenge System
Provides real-time plots for robot control parameters like position, velocity, and error
"""

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                           QLabel, QComboBox, QCheckBox, QPushButton,
                           QSplitter, QScrollArea)
from PyQt5.QtGui import QFont, QColor, QPen

class ControlVisualizerWidget(QWidget):
    """
    Widget for visualizing robot control parameters
    Provides real-time plots for position, velocity, error, and torque
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        
        # Configure plot defaults
        pg.setConfigOptions(antialias=True)
        
        # Create plot widgets
        self.position_plot = self._create_plot("Joint Position", "Time (s)", "Position (rad)")
        self.velocity_plot = self._create_plot("Joint Velocity", "Time (s)", "Velocity (rad/s)")
        self.error_plot = self._create_plot("Position Error", "Time (s)", "Error (rad)")
        self.torque_plot = self._create_plot("Motor Torque", "Time (s)", "Torque (N·m)")
        
        # Add plots to splitter
        plots_container = QWidget()
        plots_layout = QVBoxLayout(plots_container)
        plots_layout.setContentsMargins(0, 0, 0, 0)
        
        plots_layout.addWidget(self.position_plot)
        plots_layout.addWidget(self.velocity_plot)
        plots_layout.addWidget(self.error_plot)
        plots_layout.addWidget(self.torque_plot)
        
        splitter.addWidget(plots_container)
        
        # Create controls area
        controls = self._create_controls()
        splitter.addWidget(controls)
        
        # Set initial splitter sizes (more space for plots)
        splitter.setSizes([700, 100])
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Initialize data storage
        self.data = {
            'time': [],
            'position': {},  # Dictionary with joint_id as key
            'velocity': {},
            'error': {},
            'torque': {},
            'target': {}
        }
        
        # Plot items for each joint
        self.plot_items = {
            'position': {},
            'velocity': {},
            'error': {},
            'torque': {},
            'target': {}
        }
        
        # Colors for different joints (using high-contrast colors)
        self.joint_colors = [
            (255, 0, 0),     # Red
            (0, 128, 255),   # Blue
            (0, 200, 0),     # Green
            (255, 165, 0),   # Orange
            (128, 0, 128),   # Purple
            (0, 128, 128)    # Teal
        ]
        
        # Visibility flags
        self.show_target = True
        self.show_velocity = True
        self.show_error = True
        self.show_torque = True
        
        # Maximum data points to store (for performance)
        self.max_data_points = 1000
        
        # Create legend
        self.update_legend()
    
    def _create_plot(self, title, x_label, y_label):
        """Create a pyqtgraph plot widget with default styling"""
        plot = pg.PlotWidget()
        plot.setBackground('w')
        plot.setTitle(title, color="k", size="12pt")
        plot.setLabel("left", y_label, color="k")
        plot.setLabel("bottom", x_label, color="k")
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.addLegend()
        
        # Set font for axis labels
        font = QFont()
        font.setPointSize(10)
        plot.getAxis("bottom").setStyle(tickFont=font)
        plot.getAxis("left").setStyle(tickFont=font)
        
        return plot
    
    def _create_controls(self):
        """Create control panel for visualization options"""
        controls_group = QGroupBox("Visualization Controls")
        layout = QVBoxLayout(controls_group)
        
        # Joint selector
        joint_layout = QHBoxLayout()
        joint_layout.addWidget(QLabel("Select Joint:"))
        
        self.joint_selector = QComboBox()
        self.joint_selector.addItem("All Joints", "all")
        for i in range(1, 7):  # Assuming max 6 joints
            self.joint_selector.addItem(f"Joint {i}", i)
        
        self.joint_selector.currentIndexChanged.connect(self.update_plot_visibility)
        joint_layout.addWidget(self.joint_selector)
        layout.addLayout(joint_layout)
        
        # Visibility checkboxes
        checkbox_layout = QHBoxLayout()
        
        self.target_checkbox = QCheckBox("Show Target")
        self.target_checkbox.setChecked(True)
        self.target_checkbox.toggled.connect(self.toggle_target)
        checkbox_layout.addWidget(self.target_checkbox)
        
        self.velocity_checkbox = QCheckBox("Show Velocity")
        self.velocity_checkbox.setChecked(True)
        self.velocity_checkbox.toggled.connect(self.toggle_velocity)
        checkbox_layout.addWidget(self.velocity_checkbox)
        
        self.error_checkbox = QCheckBox("Show Error")
        self.error_checkbox.setChecked(True)
        self.error_checkbox.toggled.connect(self.toggle_error)
        checkbox_layout.addWidget(self.error_checkbox)
        
        self.torque_checkbox = QCheckBox("Show Torque")
        self.torque_checkbox.setChecked(True)
        self.torque_checkbox.toggled.connect(self.toggle_torque)
        checkbox_layout.addWidget(self.torque_checkbox)
        
        layout.addLayout(checkbox_layout)
        
        # Auto-range button
        button_layout = QHBoxLayout()
        
        reset_button = QPushButton("Reset View")
        reset_button.clicked.connect(self.reset_plot_ranges)
        reset_button.setMaximumWidth(150)
        button_layout.addWidget(reset_button)
        
        clear_button = QPushButton("Clear Data")
        clear_button.clicked.connect(self.clear_data)
        clear_button.setMaximumWidth(150)
        button_layout.addWidget(clear_button)
        
        layout.addLayout(button_layout)
        
        return controls_group
    
    def update_control_data(self, control_data):
        """
        Update plots with new control data
        
        Parameters:
        -----------
        control_data : dict
            Dictionary containing control data with keys:
            - 'time': list of time values
            - 'position': dict mapping joint_id to position list
            - 'velocity': dict mapping joint_id to velocity list
            - 'error': dict mapping joint_id to error list
            - 'torque': dict mapping joint_id to torque list
            - 'target': dict mapping joint_id to target position list
        """
        if not control_data:
            return
            
        # Check if we're receiving incremental data or complete dataset
        incremental = 'time' in control_data and len(control_data['time']) < 10
        
        # Update stored data
        if 'time' in control_data:
            if incremental:
                self.data['time'].extend(control_data['time'])
                # Limit data size for performance
                if len(self.data['time']) > self.max_data_points:
                    self.data['time'] = self.data['time'][-self.max_data_points:]
            else:
                self.data['time'] = control_data['time'][-self.max_data_points:]
        
        for data_type in ['position', 'velocity', 'error', 'torque', 'target']:
            if data_type in control_data:
                for joint_id, values in control_data[data_type].items():
                    # Ensure joint_id exists in data structure
                    if joint_id not in self.data[data_type]:
                        self.data[data_type][joint_id] = []
                        
                    # Add or replace data
                    if incremental:
                        self.data[data_type][joint_id].extend(values)
                        # Limit data size
                        if len(self.data[data_type][joint_id]) > self.max_data_points:
                            self.data[data_type][joint_id] = self.data[data_type][joint_id][-self.max_data_points:]
                    else:
                        self.data[data_type][joint_id] = values[-self.max_data_points:]
        
        # Update plots
        self.update_plots()
        
        # Update UI elements
        self.update_joint_selector()
        self.update_legend()
    
    def update_plots(self):
        """Update all plots with current data"""
        # Clear plots
        self.position_plot.clear()
        self.velocity_plot.clear()
        self.error_plot.clear()
        self.torque_plot.clear()
        
        # Reset plot items
        self.plot_items = {
            'position': {},
            'velocity': {},
            'error': {},
            'torque': {},
            'target': {}
        }
        
        # Get selected joint
        selected = self.joint_selector.currentData()
        
        # Time data must exist
        if not self.data['time']:
            return
            
        time_data = self.data['time']
        
        # Update position plot
        if self.data['position']:
            for joint_id, positions in self.data['position'].items():
                # Skip if not selected and not showing all
                if selected != "all" and selected != joint_id:
                    continue
                    
                # Skip if data length doesn't match
                if len(positions) != len(time_data):
                    continue
                
                # Get color index (wrap around if needed)
                color_idx = (int(joint_id) - 1) % len(self.joint_colors)
                color = self.joint_colors[color_idx]
                
                # Add position line
                pen = pg.mkPen(color=color, width=2)
                plot_item = self.position_plot.plot(time_data, positions, pen=pen, name=f"Joint {joint_id}")
                self.plot_items['position'][joint_id] = plot_item
                
                # Add target line if available
                if self.show_target and joint_id in self.data['target']:
                    targets = self.data['target'][joint_id]
                    if len(targets) == len(time_data):
                        pen = pg.mkPen(color=color, width=2, style=Qt.DashLine)
                        plot_item = self.position_plot.plot(time_data, targets, pen=pen, name=f"Target {joint_id}")
                        self.plot_items['target'][joint_id] = plot_item
        
        # Update velocity plot
        if self.show_velocity and self.data['velocity']:
            for joint_id, velocities in self.data['velocity'].items():
                # Skip if not selected and not showing all
                if selected != "all" and selected != joint_id:
                    continue
                    
                # Skip if data length doesn't match
                if len(velocities) != len(time_data):
                    continue
                
                # Get color
                color_idx = (int(joint_id) - 1) % len(self.joint_colors)
                color = self.joint_colors[color_idx]
                
                # Add velocity line
                pen = pg.mkPen(color=color, width=2)
                plot_item = self.velocity_plot.plot(time_data, velocities, pen=pen, name=f"Joint {joint_id}")
                self.plot_items['velocity'][joint_id] = plot_item
        
        # Update error plot
        if self.show_error and self.data['error']:
            for joint_id, errors in self.data['error'].items():
                # Skip if not selected and not showing all
                if selected != "all" and selected != joint_id:
                    continue
                    
                # Skip if data length doesn't match
                if len(errors) != len(time_data):
                    continue
                
                # Get color
                color_idx = (int(joint_id) - 1) % len(self.joint_colors)
                color = self.joint_colors[color_idx]
                
                # Add error line
                pen = pg.mkPen(color=color, width=2)
                plot_item = self.error_plot.plot(time_data, errors, pen=pen, name=f"Joint {joint_id}")
                self.plot_items['error'][joint_id] = plot_item
        
        # Update torque plot
        if self.show_torque and self.data['torque']:
            for joint_id, torques in self.data['torque'].items():
                # Skip if not selected and not showing all
                if selected != "all" and selected != joint_id:
                    continue
                    
                # Skip if data length doesn't match
                if len(torques) != len(time_data):
                    continue
                
                # Get color
                color_idx = (int(joint_id) - 1) % len(self.joint_colors)
                color = self.joint_colors[color_idx]
                
                # Add torque line
                pen = pg.mkPen(color=color, width=2)
                plot_item = self.torque_plot.plot(time_data, torques, pen=pen, name=f"Joint {joint_id}")
                self.plot_items['torque'][joint_id] = plot_item
    
    def update_joint_selector(self):
        """Update joint selector with available joints"""
        # Store current selection
        current = self.joint_selector.currentData()
        
        # Block signals to prevent triggering updates during changes
        self.joint_selector.blockSignals(True)
        
        # Clear and re-add "All" option
        self.joint_selector.clear()
        self.joint_selector.addItem("All Joints", "all")
        
        # Add all joints that have data
        joint_ids = set()
        for data_type in ['position', 'velocity', 'error', 'torque']:
            joint_ids.update(self.data[data_type].keys())
        
        for joint_id in sorted(joint_ids, key=lambda x: int(x) if isinstance(x, (int, str)) else 0):
            self.joint_selector.addItem(f"Joint {joint_id}", joint_id)
        
        # Restore selection if possible
        index = self.joint_selector.findData(current)
        if index >= 0:
            self.joint_selector.setCurrentIndex(index)
        
        # Unblock signals
        self.joint_selector.blockSignals(False)
    
    def update_legend(self):
        """Update plot legends"""
        # Reset legends
        self.position_plot.clear()
        self.velocity_plot.clear()
        self.error_plot.clear()
        self.torque_plot.clear()
        
        # Add back plot items
        for joint_id, plot_item in self.plot_items['position'].items():
            self.position_plot.addItem(plot_item)
        
        for joint_id, plot_item in self.plot_items['target'].items():
            self.position_plot.addItem(plot_item)
            
        for joint_id, plot_item in self.plot_items['velocity'].items():
            self.velocity_plot.addItem(plot_item)
            
        for joint_id, plot_item in self.plot_items['error'].items():
            self.error_plot.addItem(plot_item)
            
        for joint_id, plot_item in self.plot_items['torque'].items():
            self.torque_plot.addItem(plot_item)
    
    def update_plot_visibility(self):
        """Update which joints are visible based on selection"""
        self.update_plots()
    
    def toggle_target(self, checked):
        """Toggle visibility of target position lines"""
        self.show_target = checked
        self.update_plots()
    
    def toggle_velocity(self, checked):
        """Toggle visibility of velocity plot"""
        self.show_velocity = checked
        self.velocity_plot.setVisible(checked)
        self.update_plots()
    
    def toggle_error(self, checked):
        """Toggle visibility of error plot"""
        self.show_error = checked
        self.error_plot.setVisible(checked)
        self.update_plots()
    
    def toggle_torque(self, checked):
        """Toggle visibility of torque plot"""
        self.show_torque = checked
        self.torque_plot.setVisible(checked)
        self.update_plots()
    
    def reset_plot_ranges(self):
        """Reset all plots to auto-range"""
        self.position_plot.autoRange()
        self.velocity_plot.autoRange()
        self.error_plot.autoRange()
        self.torque_plot.autoRange()
    
    def clear_data(self):
        """Clear all stored data"""
        self.data = {
            'time': [],
            'position': {},
            'velocity': {},
            'error': {},
            'torque': {},
            'target': {}
        }
        
        self.update_plots()


class PDTuningWidget(QWidget):
    """
    Specialized widget for PD control tuning visualization
    Shows the effects of different PD gains on control performance
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize layout
        layout = QVBoxLayout(self)
        
        # Create response plot
        self.response_plot = pg.PlotWidget()
        self.response_plot.setBackground('w')
        self.response_plot.setTitle("Step Response", color="k", size="14pt")
        self.response_plot.setLabel("left", "Position (rad)", color="k")
        self.response_plot.setLabel("bottom", "Time (s)", color="k")
        self.response_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # Plot items
        self.target_line = self.response_plot.plot([], [], pen=pg.mkPen('k', width=2, style=Qt.DashLine), name="Target")
        self.response_line = self.response_plot.plot([], [], pen=pg.mkPen('b', width=2), name="Response")
        
        # Add vertical lines for metrics
        self.settling_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('g', width=2, style=Qt.DashLine))
        self.peak_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('r', width=2, style=Qt.DashLine))
        self.response_plot.addItem(self.settling_line)
        self.response_plot.addItem(self.peak_line)
        
        # Add metrics display
        self.metrics_widget = QGroupBox("Performance Metrics")
        metrics_layout = QHBoxLayout()
        
        # Rise time
        rise_time_layout = QVBoxLayout()
        rise_time_layout.addWidget(QLabel("Rise Time:"))
        self.rise_time_label = QLabel("N/A")
        self.rise_time_label.setStyleSheet("font-weight: bold; color: blue;")
        rise_time_layout.addWidget(self.rise_time_label)
        metrics_layout.addLayout(rise_time_layout)
        
        # Settling time
        settling_time_layout = QVBoxLayout()
        settling_time_layout.addWidget(QLabel("Settling Time:"))
        self.settling_time_label = QLabel("N/A")
        self.settling_time_label.setStyleSheet("font-weight: bold; color: green;")
        settling_time_layout.addWidget(self.settling_time_label)
        metrics_layout.addLayout(settling_time_layout)
        
        # Overshoot
        overshoot_layout = QVBoxLayout()
        overshoot_layout.addWidget(QLabel("Overshoot:"))
        self.overshoot_label = QLabel("N/A")
        self.overshoot_label.setStyleSheet("font-weight: bold; color: red;")
        overshoot_layout.addWidget(self.overshoot_label)
        metrics_layout.addLayout(overshoot_layout)
        
        # Steady-state error
        error_layout = QVBoxLayout()
        error_layout.addWidget(QLabel("Steady-State Error:"))
        self.error_label = QLabel("N/A")
        self.error_label.setStyleSheet("font-weight: bold; color: orange;")
        error_layout.addWidget(self.error_label)
        metrics_layout.addLayout(error_layout)
        
        self.metrics_widget.setLayout(metrics_layout)
        
        # Add plot and metrics to main layout
        layout.addWidget(self.response_plot)
        layout.addWidget(self.metrics_widget)
        
        # Add gains display
        gains_widget = QGroupBox("Controller Gains")
        gains_layout = QHBoxLayout()
        
        # Kp display
        kp_layout = QVBoxLayout()
        kp_layout.addWidget(QLabel("Proportional Gain (Kp):"))
        self.kp_label = QLabel("N/A")
        self.kp_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        kp_layout.addWidget(self.kp_label)
        gains_layout.addLayout(kp_layout)
        
        # Kd display
        kd_layout = QVBoxLayout()
        kd_layout.addWidget(QLabel("Derivative Gain (Kd):"))
        self.kd_label = QLabel("N/A")
        self.kd_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        kd_layout.addWidget(self.kd_label)
        gains_layout.addLayout(kd_layout)
        
        gains_widget.setLayout(gains_layout)
        layout.addWidget(gains_widget)
    
    def update_response_data(self, response_data):
        """
        Update step response visualization with new data
        
        Parameters:
        -----------
        response_data : dict
            Dictionary containing response data:
            - 'time': list of time values
            - 'position': list of position values
            - 'target': target position value
            - 'metrics': dict with performance metrics
            - 'gains': dict with controller gains
        """
        if not response_data or 'time' not in response_data or 'position' not in response_data:
            return
            
        # Extract data
        time_data = response_data['time']
        position_data = response_data['position']
        
        # Update response line
        self.response_line.setData(time_data, position_data)
        
        # Update target line if provided
        if 'target' in response_data:
            target = response_data['target']
            # Create horizontal line at target value
            target_x = [time_data[0], time_data[-1]]
            target_y = [target, target]
            self.target_line.setData(target_x, target_y)
        
        # Update metrics if provided
        if 'metrics' in response_data:
            metrics = response_data['metrics']
            
            # Update metric labels
            if 'rise_time' in metrics:
                self.rise_time_label.setText(f"{metrics['rise_time']:.3f} s")
            
            if 'settling_time' in metrics:
                self.settling_time_label.setText(f"{metrics['settling_time']:.3f} s")
                # Update settling time line
                self.settling_line.setValue(metrics['settling_time'])
                self.settling_line.setVisible(True)
            else:
                self.settling_line.setVisible(False)
            
            if 'overshoot' in metrics:
                self.overshoot_label.setText(f"{metrics['overshoot']*100:.1f}%")
            
            if 'steady_state_error' in metrics:
                self.error_label.setText(f"{metrics['steady_state_error']:.4f} rad")
            
            # Update peak line if overshoot exists
            if 'peak_time' in metrics:
                self.peak_line.setValue(metrics['peak_time'])
                self.peak_line.setVisible(True)
            else:
                self.peak_line.setVisible(False)
        
        # Update controller gains if provided
        if 'gains' in response_data:
            gains = response_data['gains']
            
            if 'kp' in gains:
                self.kp_label.setText(f"{gains['kp']:.1f}")
            
            if 'kd' in gains:
                self.kd_label.setText(f"{gains['kd']:.3f}")
        
        # Auto-range the plot
        self.response_plot.autoRange()