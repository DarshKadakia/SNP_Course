import sys
import os
import select
import json
import time
import numpy as np
from typing import Dict, Optional

# Add src/ to sys.path so challenge files can use bare imports
# (e.g. `from esp_bridge import ...`, `from utils import ...`)
_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from utils import get_config_path

# Import challenge slot mapping for display number resolution
try:
    from gui.data.challenge_mapping import get_display_number as _get_slot_display
except ImportError:
    def _get_slot_display(challenge_id): return challenge_id

# Import wrappers (only challenges in gui/data/challenge_mapping CHALLENGE_SLOT_MAP + bonus1)
from src.wrappers.AB6_SNP_SNP_HW_01_wrapper import AB6_SNP_SNP_HW_01_wrapper
from src.wrappers.AB6_SNP_SNP_HW_02_wrapper import AB6_SNP_SNP_HW_02_wrapper
from src.wrappers.AB6_CON_RBX_HW_004_wrapper import AB6_CON_RBX_HW_004_wrapper
from src.wrappers.AB6_SNP_SNP_QZ_03_wrapper import AB6_SNP_SNP_QZ_03_wrapper
from src.wrappers.AB6_SNP_SNP_HW_11_wrapper import AB6_SNP_SNP_HW_11_wrapper
from src.wrappers.AB6_SNP_SNP_HW_12_wrapper import AB6_SNP_SNP_HW_12_wrapper
from src.wrappers.AB6_SNP_SNP_HW_13_wrapper import AB6_SNP_SNP_HW_13_wrapper
from src.wrappers.AB6_SNP_SNP_HW_14_wrapper import AB6_SNP_SNP_HW_14_wrapper
from src.wrappers.AB6_SNP_SNP_HW_06_wrapper import AB6_SNP_SNP_HW_06_wrapper
from src.wrappers.AB6_SNP_SNP_HW_08_wrapper import AB6_SNP_SNP_HW_08_wrapper
from src.wrappers.AB6_SNP_SNP_HW_09_wrapper import AB6_SNP_SNP_HW_09_wrapper
from src.wrappers.AB6_SNP_SNP_HW_10_wrapper import AB6_SNP_SNP_HW_10_wrapper
from src.wrappers.AB6_SNP_SNP_HW_05_wrapper import AB6_SNP_SNP_HW_05_wrapper
from src.wrappers.BONUS_1_wrapper import BONUS_1_wrapper

# Import core challenge modules
from src.challenges.AB6_SNP_SNP_HW_01_Challenge.AB6_SNP_SNP_HW_01_Challenge import AB6_SNP_SNP_HW_01 as AB6_SNP_SNP_HW_01_Challenge
from src.challenges.AB6_SNP_SNP_HW_02_Challenge.AB6_SNP_SNP_HW_02_Challenge import AB6_SNP_SNP_HW_02_Challenge
from src.challenges.AB6_CON_RBX_HW_004_Challenge.AB6_CON_RBX_HW_004_Challenge import AB6_CON_RBX_HW_004_Challenge
from src.challenges.AB6_SNP_SNP_QZ_03_Challenge.AB6_SNP_SNP_QZ_03_Challenge import AB6_SNP_SNP_QZ_03_Challenge
from src.challenges.AB6_SNP_SNP_HW_11_Challenge.AB6_SNP_SNP_HW_11_Challenge import AB6_SNP_SNP_HW_11_Challenge
from src.challenges.AB6_SNP_SNP_HW_12_Challenge.AB6_SNP_SNP_HW_12_Challenge import AB6_SNP_SNP_HW_12_Challenge
from src.challenges.AB6_SNP_SNP_HW_13_Challenge.AB6_SNP_SNP_HW_13_Challenge import AB6_SNP_SNP_HW_13_Challenge
from src.challenges.AB6_SNP_SNP_HW_14_Challenge.AB6_SNP_SNP_HW_14_Challenge import AB6_SNP_SNP_HW_14_Challenge
from src.challenges.AB6_SNP_SNP_HW_06_Challenge.AB6_SNP_SNP_HW_06_Challenge import AB6_SNP_SNP_HW_06_Challenge
from src.challenges.AB6_SNP_SNP_HW_08_Challenge.AB6_SNP_SNP_HW_08_Challenge import AB6_SNP_SNP_HW_08_Challenge
from src.challenges.AB6_SNP_SNP_HW_09_Challenge.AB6_SNP_SNP_HW_09_Challenge import AB6_SNP_SNP_HW_09_Challenge
from src.challenges.AB6_SNP_SNP_HW_10_Challenge.AB6_SNP_SNP_HW_10_Challenge import AB6_SNP_SNP_HW_10_Challenge
from src.challenges.AB6_SNP_SNP_HW_05_Challenge.AB6_SNP_SNP_HW_05_Challenge import AB6_SNP_SNP_HW_05_Challenge
from src.challenges.BONUS_1_Challenge.BONUS_1_Challenge import BONUS_1_Challenge

from src.esp_bridge import ESPActuatorController as ActuatorController
from src.robot_core.robot_model import Robot

# =============================================================================
# ROBOT TYPE SELECTION
# =============================================================================
# Set the robot type here or use environment variable ROBOT_TYPE
# Options: "franka", "omx", "robox" (ESP-based)
# 
# You can also set this via environment variable:
#   export ROBOT_TYPE=franka
#   export ROBOT_TYPE=omx  
#   export ROBOT_TYPE=robox
# =============================================================================

ROBOT_TYPE = os.environ.get("ROBOT_TYPE", "snp").lower()

# Robot-specific configurations
FRANKA_ROBOT_IP = "192.168.1.11"
SNP_MODE = os.environ.get("SNP_MODE", "wifi").lower()
SNP_PORT = os.environ.get("SNP_PORT", "COM7")
SNP_IP   = os.environ.get("SNP_IP", "192.168.1.100")

# Dynamic import based on robot type
def get_robot_and_controller(robot_type: str):
    """
    Dynamically import and return the appropriate Robot and ActuatorController classes.
    
    :param robot_type: One of "franka", "omx", or "robox"
    :return: Tuple of (RobotClass, ActuatorControllerClass, init_kwargs)
    """
    robot_type = robot_type.lower()
    
    if robot_type == "franka":
        from src.robot_core.franka_robot_model import FrankaRobot
        from src.franka_bridge.franka_controller import FrankaController
        return FrankaRobot, FrankaController, {
            "robot_kwargs": {"name": "FR3"},
            "controller_kwargs": {"robot_ip": FRANKA_ROBOT_IP}
        }
    
    elif robot_type == "omx":
        from src.robot_core.robot_model import Robot
        from src.omx_bridge import OMXActuatorController
        return Robot, OMXActuatorController, {
            "robot_kwargs": {"config_file": "omx_robot_parameters.json"},
            "controller_kwargs": {"config_file": "omx_actuator_config.json"},
            "use_from_config": True
        }
    
    elif robot_type == "robox":
        from src.robot_core.robot_model import Robot
        from src.esp_bridge import ESPActuatorController
        return Robot, ESPActuatorController, {
            "robot_kwargs": {"config_file": "robot_parameters.json"},
            "controller_kwargs": {"config_file": "actuator_config.json"},
            "use_from_config": True
        }
    
    elif robot_type == "snp":
        from src.robot_core.snp_model import RobotModel
        from src.snp_bridge.snp_esp_bridge import SNPBridgeController
        if SNP_MODE == "wifi":
            robot_kwargs = {"mode": "wifi", "robot_ip": SNP_IP, "robot_port": 8080, "local_port": 8080}
        else:
            robot_kwargs = {"mode": "serial", "port": SNP_PORT}

        return RobotModel, SNPBridgeController, {
            "robot_kwargs": robot_kwargs,
            "controller_kwargs": {},
            "use_from_config": False
        }

    
    else:
        raise ValueError(f"Unknown robot type: {robot_type}. Choose from: franka, omx, robox")

print(f"[ChallengeRunner] Robot type: {ROBOT_TYPE}")


class ChallengeRunner:
    """
    Orchestrates the execution of all robot control challenges.
    Manages challenge initialization, execution, and cleanup.
    """

    def __init__(self, robot_config: str, actuator_config: str,
                 challenge_config: str,
                 user_interface=None):
        self.ui = user_interface
        self.wrappers = {}  # Initialize empty wrappers dict first
        self.robot = None
        self.actuator_control_instance = None
        self.load_configurations(challenge_config)

        try:
            self.initialize_components(robot_config, actuator_config)
        except Exception as e:
            import traceback
            print(f"Error initializing challenge runner: {e}")
            traceback.print_exc()

    def load_configurations(self, challenge_config: str):
        """Load challenge configurations."""
        self.config = {}
        try:
            config_path = get_config_path(challenge_config)
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Error loading challenge config: {e}")

    def initialize_components(self, robot_config: str, actuator_config: str):
        """Initialize all control components and wrappers."""
        # self.wrappers = {}
        # self._init_error = None
        try:

            # Get the appropriate robot and controller classes based on ROBOT_TYPE
            RobotClass, ControllerClass, init_config = get_robot_and_controller(ROBOT_TYPE)
            
            # Initialize robot
            print(f"Initializing {ROBOT_TYPE.upper()} Robot...")
            if init_config.get("use_from_config", False):
                # For OMX and ROBOX - use from_config method
                self.robot = RobotClass.from_config(init_config["robot_kwargs"]["config_file"])
            else:
                # For Franka - direct initialization
                self.robot = RobotClass(**init_config["robot_kwargs"])
            print(f"{ROBOT_TYPE.upper()} Robot initialized successfully")
            
            # Initialize controller
            print(f"Initializing {ROBOT_TYPE.upper()} Controller...")
            if ROBOT_TYPE == "snp":
                self.actuator_control_instance = self.robot._bridge
            elif init_config.get("use_from_config", False):
                # For OMX and ROBOX - pass config file
                self.actuator_control_instance = ControllerClass(init_config["controller_kwargs"]["config_file"])
            else:
                # For Franka - pass kwargs directly
                self.actuator_control_instance = ControllerClass(**init_config["controller_kwargs"])
            print(f"{ROBOT_TYPE.upper()} Controller initialized successfully")


            # self.robot = Robot.from_config(robot_config)
            # self.actuator_control_instance = ActuatorController(actuator_config)

            self.AB6_SNP_SNP_HW_01_task_instance = AB6_SNP_SNP_HW_01_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_02_task_instance = AB6_SNP_SNP_HW_02_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_CON_RBX_HW_004_task_instance = AB6_CON_RBX_HW_004_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_QZ_03_task_instance = AB6_SNP_SNP_QZ_03_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_11_task_instance = AB6_SNP_SNP_HW_11_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_12_task_instance = AB6_SNP_SNP_HW_12_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_13_task_instance = AB6_SNP_SNP_HW_13_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_14_task_instance = AB6_SNP_SNP_HW_14_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_06_task_instance = AB6_SNP_SNP_HW_06_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_08_task_instance = AB6_SNP_SNP_HW_08_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_09_task_instance = AB6_SNP_SNP_HW_09_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_10_task_instance = AB6_SNP_SNP_HW_10_Challenge(
                self.robot, self.actuator_control_instance)
            self.AB6_SNP_SNP_HW_05_task_instance = AB6_SNP_SNP_HW_05_Challenge(
                self.robot, self.actuator_control_instance)
            self.BONUS_1_task_instance = BONUS_1_Challenge(
                self.robot, self.actuator_control_instance)

            self.wrappers = {
                'AB6_SNP_SNP_HW_01':   AB6_SNP_SNP_HW_01_wrapper(self.AB6_SNP_SNP_HW_01_task_instance, self.ui),
                'AB6_SNP_SNP_HW_02':   AB6_SNP_SNP_HW_02_wrapper(self.AB6_SNP_SNP_HW_02_task_instance, self.ui),
                'AB6_CON_RBX_HW_004':  AB6_CON_RBX_HW_004_wrapper(self.AB6_CON_RBX_HW_004_task_instance, self.ui),
                'AB6_SNP_SNP_QZ_03':   AB6_SNP_SNP_QZ_03_wrapper(self.AB6_SNP_SNP_QZ_03_task_instance, self.ui),
                'AB6_SNP_SNP_HW_11':   AB6_SNP_SNP_HW_11_wrapper(self.AB6_SNP_SNP_HW_11_task_instance, self.ui),
                'AB6_SNP_SNP_HW_12':   AB6_SNP_SNP_HW_12_wrapper(self.AB6_SNP_SNP_HW_12_task_instance, self.ui),
                'AB6_SNP_SNP_HW_13':   AB6_SNP_SNP_HW_13_wrapper(self.AB6_SNP_SNP_HW_13_task_instance, self.ui),
                'AB6_SNP_SNP_HW_14':   AB6_SNP_SNP_HW_14_wrapper(self.AB6_SNP_SNP_HW_14_task_instance, self.ui),
                'AB6_SNP_SNP_HW_06':   AB6_SNP_SNP_HW_06_wrapper(self.AB6_SNP_SNP_HW_06_task_instance, self.ui),
                'AB6_SNP_SNP_HW_08':   AB6_SNP_SNP_HW_08_wrapper(self.AB6_SNP_SNP_HW_08_task_instance, self.ui),
                'AB6_SNP_SNP_HW_09':   AB6_SNP_SNP_HW_09_wrapper(self.AB6_SNP_SNP_HW_09_task_instance, self.ui),
                'AB6_SNP_SNP_HW_10':   AB6_SNP_SNP_HW_10_wrapper(self.AB6_SNP_SNP_HW_10_task_instance, self.ui),
                'AB6_SNP_SNP_HW_05':   AB6_SNP_SNP_HW_05_wrapper(self.AB6_SNP_SNP_HW_05_task_instance, self.ui),
                'BONUS_1':             BONUS_1_wrapper(self.BONUS_1_task_instance, self.ui),
            }

        except Exception as e:
            import traceback
            self._init_error = str(e)
            print(f"Error initializing components: {e}")
            traceback.print_exc()
            # Initialize empty wrappers dict to prevent 'no attribute' error
            self.wrappers = {}
            self.robot = None
            self.actuator_control_instance = None

    def run_challenge(self, challenge_id: str, parameters: Optional[Dict] = None) -> Dict:
        """
        Run a specific challenge.

        :param challenge_id: Challenge identifier (e.g. AB6_SNP_SNP_HW_01)
        :param parameters: Optional challenge parameters
        :return: Challenge results
        """
        if not self.wrappers:
            error_msg = self._init_error or 'Component initialization failed'
            return {'error': f'Hardware initialization failed: {error_msg}'}

        try:
            if challenge_id not in self.config:
                return {'error': f'Challenge {challenge_id} not found'}

            challenge_config = self.config[challenge_id]
            challenge_config.update(parameters or {})

            if challenge_id in ['AB6_SNP_SNP_HW_01']:
                return self._run_AB6_SNP_SNP_HW_01_challenge(challenge_id, challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_02':
                return self._run_AB6_SNP_SNP_HW_02_challenge(challenge_config)
            elif challenge_id == 'AB6_CON_RBX_HW_004':
                return self._run_AB6_CON_RBX_HW_004_challenge(challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_QZ_03':
                return self._run_AB6_SNP_SNP_QZ_03_challenge(challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_11':
                return self._run_AB6_SNP_SNP_HW_11_challenge(self.wrappers['AB6_SNP_SNP_HW_11'], challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_12':
                return self._run_AB6_SNP_SNP_HW_12_challenge(self.wrappers['AB6_SNP_SNP_HW_12'], challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_13':
                return self._run_AB6_SNP_SNP_HW_13_challenge(self.wrappers['AB6_SNP_SNP_HW_13'], challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_14':
                return self._run_AB6_SNP_SNP_HW_14_challenge(self.wrappers['AB6_SNP_SNP_HW_14'], challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_06':
                return self._run_AB6_SNP_SNP_HW_06_challenge(self.wrappers['AB6_SNP_SNP_HW_06'], challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_08':
                return self._run_AB6_SNP_SNP_HW_08_challenge(self.wrappers['AB6_SNP_SNP_HW_08'], challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_09':
                return self._run_AB6_SNP_SNP_HW_09_challenge(self.wrappers['AB6_SNP_SNP_HW_09'], challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_10':
                return self._run_AB6_SNP_SNP_HW_10_challenge(self.wrappers['AB6_SNP_SNP_HW_10'], challenge_config)
            elif challenge_id == 'BONUS_1':
                return self._run_BONUS_1_challenge(self.wrappers['BONUS_1'], challenge_config)
            elif challenge_id == 'AB6_SNP_SNP_HW_05':
                return self._run_AB6_SNP_SNP_HW_05_challenge(challenge_config)
            else:
                return {'error': 'Invalid challenge ID'}

        except Exception as e:
            return {'error': str(e)}
        finally:
            self._cleanup_challenge(challenge_id)

    def _run_AB6_SNP_SNP_HW_01_challenge(self, challenge_id: str, config: Dict) -> Dict:
        """Run sensor state identification challenge (AB6_SNP_SNP_HW_01)."""
        wrapper = self.wrappers[challenge_id]

        # GUI mode: session managed by the GUI widget
        if config.get('gui_mode', False):
            if config.get('start_task_only', False):
                success = wrapper.start_identification_session()
                if not success:
                    return {'error': 'Failed to start sensor identification session'}
                return {'status': 'Session started'}
            # Submit path — GUI passes user_answers in config
            user_answers = config.get('user_answers', {})
            passed, results = wrapper.submit_answers(user_answers)
            return results

        # Terminal / CLI path
        if not wrapper.start_identification_session():
            return {'error': 'Failed to start session'}

        self.display_message(
            "\nInteract with the robot and observe the sensor streams. "
            "When ready, press Enter to submit your identification results..."
        )
        input()

        user_answers = config.get('user_answers', {})
        passed, results = wrapper.submit_answers(user_answers)
        return results

    def _run_AB6_SNP_SNP_HW_02_challenge(self, config: Dict) -> Dict:
        """Run Sensor Output Nature (AB6_SNP_SNP_HW_02) — GUI-first; optional CLI hook."""
        wrapper = None
        try:
            wrapper = self.wrappers['AB6_SNP_SNP_HW_02']
            if config.get('gui_mode', False):
                if config.get('start_task_only', False):
                    if not wrapper.start_identification_session():
                        return {'error': 'Failed to start Sensor Output Nature session'}
                    return {'status': 'Session started', 'challenge_id': 'AB6_SNP_SNP_HW_02'}
                user_answers = config.get('user_answers', {})
                passed, results = wrapper.submit_answers(user_answers)
                results['passed'] = passed
                results['challenge_id'] = 'AB6_SNP_SNP_HW_02'
                results['challenge_name'] = config.get('name', 'Sensor Output Nature')
                return results
            if not wrapper.start_identification_session():
                return {'error': 'Failed to start session'}
            self.display_message(
                f"\nChallenge {_get_slot_display('AB6_SNP_SNP_HW_02')} — Sensor Output Nature "
                "is completed in the desktop application (live sensor streams, two parts)."
            )
            return {
                'status': 'gui_required',
                'challenge_id': 'AB6_SNP_SNP_HW_02',
                'challenge_name': config.get('name', 'Sensor Output Nature'),
            }
        except Exception as e:
            return {'error': str(e)}
        finally:
            if wrapper is not None:
                wrapper.cleanup()

    def _run_AB6_CON_RBX_HW_004_challenge(self, config: Dict) -> Dict:
        """Run position control challenge (AB6_CON_RBX_HW_004)."""
        wrapper = self.wrappers['AB6_CON_RBX_HW_004']

        try:
            if self.ui:
                kp = config.get('kp', 400)
                kd = config.get('kd', 0)
                self.display_message("\nUser Story:")
                self.display_message("This training program is the control system training program for controlling robot joints.\n")
                self.display_message(f"This is challenge {_get_slot_display('AB6_CON_RBX_HW_004')}, first joint of the robot is set for you to control through tuning Kp and Kd gains.")
                self.display_message(f"Using Kp={kp}, Kd={kd}")
            else:
                self.display_message("\nUser Story:")
                self.display_message("This training program is the control system training program for controlling robot joints.\n")
                self.display_message(f"This is challenge {_get_slot_display('AB6_CON_RBX_HW_004')}, first joint of the robot is set for you to control through tuning Kp and Kd gains. Kp is in the range [200, 12000] and Kd in the range [0,10]. Once you have entered the values, the joint will try to go to the target angle of 90 degrees and settle, use the graphs and post generated data to finetune the Kp and Kd values. \nEnter PD control gains:")
                kp = float(input("Enter Kp value: "))
                kd = float(input("Enter Kd value: "))

            success = wrapper.start_position_control_experiment(
                config['target_angle'], kp, kd)

            if not success:
                return {'error': 'Failed to start experiment'}

            while True:
                completed, results = wrapper.check_experiment_completion()
                if completed:
                    break
                time.sleep(0.01)

            wrapper.plot_control_performance()
            return results

        except ValueError:
            return {'error': 'Invalid input. Please enter numeric values for Kp and Kd'}
        except Exception as e:
            return {'error': str(e)}
        finally:
            try:
                wrapper.cleanup()
                self._cleanup_challenge('AB6_CON_RBX_HW_004')
                for actuator_id in self.actuator_control_instance.actuators:
                    self.actuator_control_instance.disable_torque(actuator_id)
            except Exception:
                for actuator_id in self.actuator_control_instance.actuators:
                    try:
                        self.actuator_control_instance.disable_torque(actuator_id)
                    except Exception:
                        pass

    @staticmethod
    def check_input():
        """Check if input is available (non-blocking)."""
        if sys.platform == 'win32':
            import msvcrt
            return msvcrt.kbhit()
        else:
            r, _, _ = select.select([sys.stdin], [], [], 0)
            return sys.stdin in r and sys.stdin.readline()

    def _cleanup_challenge(self, challenge_id: str):
        """Clean up after challenge execution."""
        try:
            w = self.wrappers.get(challenge_id)
            if w is not None:
                w.cleanup()
        except Exception:
            pass

    def _run_AB6_SNP_SNP_QZ_03_challenge(self, config: Dict) -> Dict:
        """Run sensor principles quiz challenge (AB6_SNP_SNP_QZ_03)."""
        try:
            wrapper = self.wrappers['AB6_SNP_SNP_QZ_03']

            if not wrapper.start_quiz():
                return {'error': 'Failed to start quiz'}

            if self.ui:
                return {
                    'status': 'quiz_started',
                    'challenge_id': 'AB6_SNP_SNP_QZ_03',
                }

            return {
                'status': 'quiz_started',
                'challenge_id': 'AB6_SNP_SNP_QZ_03',
                'challenge_name': config['name'],
            }

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def display_message(self, message: str):
        """Display message to user."""
        if self.ui:
            self.ui.display_message(message)
        else:
            print(message)

    def get_challenge_status(self, challenge_id: str) -> Dict:
        """
        Get current status of a challenge.

        :param challenge_id: Challenge identifier
        :return: Challenge status
        """
        try:
            if challenge_id not in self.wrappers:
                return {'error': f'Challenge {challenge_id} not found'}
            return self.wrappers[challenge_id].get_task_status()
        except Exception as e:
            return {'error': str(e)}

    def _run_AB6_SNP_SNP_HW_12_challenge(self, wrapper, config: Dict) -> Dict:
        """Run Teach by Touch (AB6_SNP_SNP_HW_12) — CLI path mirrors TM_016 / HW_10."""
        try:
            target_position = None
            if 'target_position' in config:
                target_position = np.array([
                    config['target_position']['x'],
                    config['target_position']['y'],
                    config['target_position']['z']
                ])

            if not wrapper.start_challenge(target_position):
                return {'error': 'Failed to start challenge'}

            self.display_message("\nEdit the template file with your solution and press Enter when ready...")

            if not wrapper.run_user_solution():
                return {'error': 'Failed to run user solution'}

            self.display_message("\nMonitoring challenge progress...")
            self.display_message("Press Enter when you want to stop the challenge...")

            wrapper.stop_challenge()
            completed, results = wrapper.check_task_completion()

            results.update({
                'challenge_id': 'AB6_SNP_SNP_HW_12',
                'challenge_name': config['name'],
                'parameters': {
                    'target_position': config.get('target_position', wrapper.control.target_position.tolist())
                }
            })
            return results

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def _run_AB6_SNP_SNP_HW_13_challenge(self, wrapper, config: Dict) -> Dict:
        """Run Survive the Failure (AB6_SNP_SNP_HW_13) — CLI path mirrors HW_12."""
        try:
            target_position = None
            if 'target_position' in config:
                target_position = np.array([
                    config['target_position']['x'],
                    config['target_position']['y'],
                    config['target_position']['z']
                ])

            if not wrapper.start_challenge(target_position):
                return {'error': 'Failed to start challenge'}

            self.display_message("\nEdit the template file with your solution and press Enter when ready...")

            if not wrapper.run_user_solution():
                return {'error': 'Failed to run user solution'}

            self.display_message("\nMonitoring challenge progress...")
            self.display_message("Press Enter when you want to stop the challenge...")

            wrapper.stop_challenge()
            completed, results = wrapper.check_task_completion()

            results.update({
                'challenge_id': 'AB6_SNP_SNP_HW_13',
                'challenge_name': config['name'],
                'parameters': {
                    'target_position': config.get('target_position', wrapper.control.target_position.tolist())
                }
            })
            return results

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def _run_AB6_SNP_SNP_HW_14_challenge(self, wrapper, config: Dict) -> Dict:
        """Run Teleoperation (AB6_SNP_SNP_HW_14) — CLI path mirrors HW_13."""
        try:
            target_position = None
            if 'target_position' in config:
                target_position = np.array([
                    config['target_position']['x'],
                    config['target_position']['y'],
                    config['target_position']['z']
                ])

            if not wrapper.start_challenge(target_position):
                return {'error': 'Failed to start challenge'}

            self.display_message("\nEdit the template file with your solution and press Enter when ready...")

            if not wrapper.run_user_solution():
                return {'error': 'Failed to run user solution'}

            self.display_message("\nMonitoring challenge progress...")
            self.display_message("Press Enter when you want to stop the challenge...")

            wrapper.stop_challenge()
            completed, results = wrapper.check_task_completion()

            results.update({
                'challenge_id': 'AB6_SNP_SNP_HW_14',
                'challenge_name': config['name'],
                'parameters': {
                    'target_position': config.get('target_position', wrapper.control.target_position.tolist())
                }
            })
            return results

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def _run_AB6_SNP_SNP_HW_06_challenge(self, wrapper, config: Dict) -> Dict:
        """Run The Right Sensor for the Right Job (AB6_SNP_SNP_HW_06) — CLI path mirrors TM_016."""
        try:
            target_position = None
            if 'target_position' in config:
                target_position = np.array([
                    config['target_position']['x'],
                    config['target_position']['y'],
                    config['target_position']['z']
                ])

            if not wrapper.start_challenge(target_position):
                return {'error': 'Failed to start challenge'}

            self.display_message("\nEdit the template file with your solution and press Enter when ready...")

            if not wrapper.run_user_solution():
                return {'error': 'Failed to run user solution'}

            self.display_message("\nMonitoring challenge progress...")
            self.display_message("Press Enter when you want to stop the challenge...")

            wrapper.stop_challenge()
            completed, results = wrapper.check_task_completion()

            results.update({
                'challenge_id': 'AB6_SNP_SNP_HW_06',
                'challenge_name': config['name'],
                'parameters': {
                    'target_position': config.get('target_position', wrapper.control.target_position.tolist())
                }
            })
            return results

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def _run_AB6_SNP_SNP_HW_08_challenge(self, wrapper, config: Dict) -> Dict:
        """Run Navigate and Map (AB6_SNP_SNP_HW_08) — CLI path mirrors AB6_SNP_SNP_HW_06 / TM_016."""
        try:
            target_position = None
            if 'target_position' in config:
                target_position = np.array([
                    config['target_position']['x'],
                    config['target_position']['y'],
                    config['target_position']['z']
                ])

            if not wrapper.start_challenge(target_position):
                return {'error': 'Failed to start challenge'}

            self.display_message("\nEdit the template file with your solution and press Enter when ready...")

            if not wrapper.run_user_solution():
                return {'error': 'Failed to run user solution'}

            self.display_message("\nMonitoring challenge progress...")
            self.display_message("Press Enter when you want to stop the challenge...")

            wrapper.stop_challenge()
            completed, results = wrapper.check_task_completion()

            results.update({
                'challenge_id': 'AB6_SNP_SNP_HW_08',
                'challenge_name': config['name'],
                'parameters': {
                    'target_position': config.get('target_position', wrapper.control.target_position.tolist())
                }
            })
            return results

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def _run_AB6_SNP_SNP_HW_09_challenge(self, wrapper, config: Dict) -> Dict:
        """Run Precision Line Tracking (AB6_SNP_SNP_HW_09) — CLI path mirrors AB6_SNP_SNP_HW_08 / TM_016."""
        try:
            target_position = None
            if 'target_position' in config:
                target_position = np.array([
                    config['target_position']['x'],
                    config['target_position']['y'],
                    config['target_position']['z']
                ])

            if not wrapper.start_challenge(target_position):
                return {'error': 'Failed to start challenge'}

            self.display_message("\nEdit the template file with your solution and press Enter when ready...")

            if not wrapper.run_user_solution():
                return {'error': 'Failed to run user solution'}

            self.display_message("\nMonitoring challenge progress...")
            self.display_message("Press Enter when you want to stop the challenge...")

            wrapper.stop_challenge()
            completed, results = wrapper.check_task_completion()

            results.update({
                'challenge_id': 'AB6_SNP_SNP_HW_09',
                'challenge_name': config['name'],
                'parameters': {
                    'target_position': config.get('target_position', wrapper.control.target_position.tolist())
                }
            })
            return results

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def _run_AB6_SNP_SNP_HW_10_challenge(self, wrapper, config: Dict) -> Dict:
        """Run Precision Docking (AB6_SNP_SNP_HW_10) — CLI path mirrors AB6_SNP_SNP_HW_09."""
        try:
            target_position = None
            if 'target_position' in config:
                target_position = np.array([
                    config['target_position']['x'],
                    config['target_position']['y'],
                    config['target_position']['z']
                ])

            if not wrapper.start_challenge(target_position):
                return {'error': 'Failed to start challenge'}

            self.display_message("\nEdit the template file with your solution and press Enter when ready...")

            if not wrapper.run_user_solution():
                return {'error': 'Failed to run user solution'}

            self.display_message("\nMonitoring challenge progress...")
            self.display_message("Press Enter when you want to stop the challenge...")

            wrapper.stop_challenge()
            completed, results = wrapper.check_task_completion()

            results.update({
                'challenge_id': 'AB6_SNP_SNP_HW_10',
                'challenge_name': config['name'],
                'parameters': {
                    'target_position': config.get('target_position', wrapper.control.target_position.tolist())
                }
            })
            return results

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def _run_AB6_SNP_SNP_HW_11_challenge(self, wrapper, config: Dict) -> Dict:
        """Run Code Unlock — Pressure Sequence (AB6_SNP_SNP_HW_11) — CLI path mirrors HW_10."""
        try:
            target_position = None
            if 'target_position' in config:
                target_position = np.array([
                    config['target_position']['x'],
                    config['target_position']['y'],
                    config['target_position']['z']
                ])

            if not wrapper.start_challenge(target_position):
                return {'error': 'Failed to start challenge'}

            self.display_message("\nEdit the template file with your solution and press Enter when ready...")

            if not wrapper.run_user_solution():
                return {'error': 'Failed to run user solution'}

            self.display_message("\nMonitoring challenge progress...")
            self.display_message("Press Enter when you want to stop the challenge...")

            wrapper.stop_challenge()
            completed, results = wrapper.check_task_completion()

            results.update({
                'challenge_id': 'AB6_SNP_SNP_HW_11',
                'challenge_name': config['name'],
                'parameters': {
                    'target_position': config.get('target_position', wrapper.control.target_position.tolist())
                }
            })
            return results

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def _run_AB6_SNP_SNP_HW_05_challenge(self, config: Dict) -> Dict:
        """Run Sense It Your Way challenge (AB6_SNP_SNP_HW_05)."""
        try:
            wrapper = self.wrappers['AB6_SNP_SNP_HW_05']
            if not wrapper.start_challenge():
                return {'error': 'Failed to start challenge'}
            if self.ui:
                return {
                    'status': 'challenge_started',
                    'challenge_id': 'AB6_SNP_SNP_HW_05',
                }
            return {
                'status': 'challenge_started',
                'challenge_id': 'AB6_SNP_SNP_HW_05',
                'challenge_name': config['name'],
            }
        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def _run_BONUS_1_challenge(self, wrapper, config: Dict) -> Dict:
        """Run BONUS_1 Challenge."""
        try:
            if not wrapper.start_challenge():
                return {'error': 'Failed to start challenge'}

            self.display_message("\nEdit the template file with your solution and press Enter when ready...")

            if not wrapper.run_user_solution():
                return {'error': 'Failed to run user solution'}

            self.display_message("\nMonitoring challenge progress...")
            self.display_message("Press Enter when you want to stop the challenge...")

            wrapper.stop_challenge()
            completed, results = wrapper.check_task_completion()

            results.update({
                'challenge_id': 'BONUS_1',
                'challenge_name': config['name'],
            })
            return results

        except Exception as e:
            return {'error': str(e)}
        finally:
            wrapper.cleanup()

    def cleanup(self):
        """Clean up all components."""
        try:
            for wrapper in self.wrappers.values():
                wrapper.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {e}")


def run_selected_challenge(runner):
    """Run a specific challenge based on user selection."""
    challenges = {
        1:  {"id": "AB6_SNP_SNP_HW_01",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_01')} - Sensor State Identification",   "params": None},
        2:  {"id": "AB6_SNP_SNP_HW_02",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_02')} - Sensor Output Nature",       "params": None},
        3:  {"id": "AB6_SNP_SNP_QZ_03",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_QZ_03')} - Sensor Principles Quiz",      "type": "internal_quiz"},
        4:  {"id": "AB6_CON_RBX_HW_004", "name": f"Challenge {_get_slot_display('AB6_CON_RBX_HW_004')} - PD Gain Tuning",            "params": {"target_angle": 1.5}},
        5:  {"id": "AB6_SNP_SNP_HW_05",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_05')} - Sense It Your Way",          "params": None},
        6:  {"id": "AB6_SNP_SNP_HW_06",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_06')} - The Right Sensor for the Job", "params": {}},
        7:  {"id": "AB6_SNP_SNP_VZ_07",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_VZ_07')} - Sensor Filtering (GUI only)", "params": None},
        8:  {"id": "AB6_SNP_SNP_HW_08",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_08')} - Navigate and Map",           "params": {}},
        9:  {"id": "AB6_SNP_SNP_HW_09",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_09')} - Precision Line Tracking",    "params": {}},
        10: {"id": "AB6_SNP_SNP_HW_10",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_10')} - Precision Docking",          "params": {}},
        11: {"id": "AB6_SNP_SNP_HW_11",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_11')} - Code Unlock / Pressure",   "params": {}},
        12: {"id": "AB6_SNP_SNP_HW_12",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_12')} - Teach by Touch",              "params": {}},
        13: {"id": "AB6_SNP_SNP_HW_13",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_13')} - Survive the Failure",           "params": {}},
        14: {"id": "AB6_SNP_SNP_HW_14",  "name": f"Challenge {_get_slot_display('AB6_SNP_SNP_HW_14')} - Teleoperation",                  "params": {}},
        15: {"id": "BONUS_1",            "name": "Bonus Challenge 1", "params": None},
    }

    while True:
        for num, challenge in challenges.items():
            print(f"{num}. {challenge['name']}")
        print("0. Exit")

        try:
            choice = int(input("\nEnter challenge number (0 to exit): "))

            if choice == 0:
                break

            if choice not in challenges:
                print("Invalid choice. Please try again.")
                continue

            challenge = challenges[choice]
            print(f"\nRunning {challenge['name']}...")

            if challenge.get('type') == 'internal_quiz':
                result = runner.run_challenge(challenge['id'])
                print("\nQuiz completed!")
                continue

            if choice == 1:
                total_score = 0
                feedback_list = []

                task_types = ['absolute', 'relative']
                task_types.append(np.random.choice(['absolute', 'relative']))
                np.random.shuffle(task_types)

                print("\n Challenge Story")
                print("\nYou are a newly recruited engineer at AB6 Robotics, assigned to the Sensing & Perception team. Multiple sensor streams are updating in real time — all unlabeled. Interact with the robot and identify what each data stream represents.\n")
                print(f"This is challenge {_get_slot_display('AB6_SNP_SNP_HW_01')}: observe the live sensor readings and label each stream. Submit once you are confident.")

                for i, task_type in enumerate(task_types):
                    print(f"\nPart {i+1}/3 of Challenge {_get_slot_display('AB6_SNP_SNP_HW_01')}")

                    if task_type == 'absolute':
                        first_angle = 5 * np.random.randint(0, 37)
                        if first_angle > 0:
                            min_second = first_angle - 90
                            count_min_second = min_second // 5
                            max_second = first_angle + 90
                            count_max_second = max_second // 5
                            second_angle = 5 * np.random.randint(count_min_second, count_max_second)
                            if second_angle > -90:
                                min_third = second_angle - 90
                                count_min_third = min_third // 5
                                max_third = second_angle + 90
                                count_max_third = max_third // 5
                                third_angle = 5 * np.random.randint(count_min_third, count_max_third)
                            else:
                                second_angle = 90
                                third_angle = 75
                        random_angles = [first_angle, second_angle, third_angle]

                        print(f"Absolute Angle Task - Target angles: {random_angles}")
                        result = runner.run_challenge('AB6_SNP_SNP_HW_01', {
                            'target_angles': random_angles
                        })
                    else:
                        random_angles = [
                            5 * np.random.randint(0, 37),
                            5 * np.random.randint(-18, 19),
                            5 * np.random.randint(-18, 19)
                        ]
                        print(f"Relative Angle Task - Target angles: {random_angles}")
                        result = runner.run_challenge('AB6_SNP_SNP_HW_01b', {
                            'relative_joint_angles': random_angles
                        })

                    total_score += result['score']
                    feedback_list.append(f"Part {i+1} ({task_type}): {result['feedback']}")

                    print(f"\nPart {i+1} Results:")
                    print(f"Score: {result['score']}")
                    print(f"Feedback: {result['feedback']}")

                    if i < 2:
                        input("\nPress Enter to continue to the next part...")

                average_score = total_score / 3
                print(f"\nChallenge {_get_slot_display('AB6_SNP_SNP_HW_01')} Complete!")
                print("-------------------")
                print(f"Average Score: {average_score:.2f}")
                print("\nFeedback Summary:")
                for fb in feedback_list:
                    print(f"- {fb}")

            else:
                result = runner.run_challenge(challenge['id'], challenge['params'])

        except ValueError:
            print("Invalid input. Please enter a number.")
        except Exception as e:
            print(f"Error running challenge: {str(e)}")


if __name__ == "__main__":
    runner = ChallengeRunner(
        'robot_parameters.json',
        'actuator_config.json',
        'challenge_config.json'
    )

    try:
        run_selected_challenge(runner)
    finally:
        ctrl = getattr(runner, "actuator_control_instance", None)
        if ctrl and hasattr(ctrl, "disable_torque"):
            for joint_id in [1, 2, 3]:
                try:
                    ctrl.disable_torque(joint_id)
                except Exception:
                    pass