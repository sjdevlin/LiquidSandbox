from hardware import CameraControllerFactory, StageControllerFactory, IlluminationControllerFactory, FocusControllerFactory
from datetime import datetime
from services import Logger, AppConfig
from models import Experiment, Sample, ImageSet, ImageRun, Image
from time import sleep

class ImageRunOperator:
    def __init__(self, image_set, experiment, db):
        self.db = db
        self.logger = Logger()
        self.app_config = AppConfig()
        self.image_set = image_set
        self.experiment = experiment
        self.plate = self.db.get_plate_by_id(self.experiment.plate_id)

        camera_type = self.app_config.get("camera_type", "default_camera") #change to do this in the camera initialization
        self.camera_controller = CameraControllerFactory.create_camera_controller(camera_type)

        self.stage_controller = StageControllerFactory.create_stage_controller()
        self.illumination_controller = IlluminationControllerFactory.create_illumination_controller()
        self.focus_controller = FocusControllerFactory.create_focus_controller()


    def run(self):
        # Calculate experiment duration and build per-minute target temperature profile

        self.start_date_time = datetime.now()

        for sample in self.experiment.sample:

            self.logger.info(f"Processing sample {sample.id} at well ({sample.well_row}, {sample.well_column})")                
            self.move_to_well(sample.well_index)

            self.illumination_controller.set_intensity(self.app_config.get("illumination_intensity", 100))
            self.focus_controller.set_focus_position(self.app_config.get("focus_position", 0))

            self.camera_controller.set_shutter_speed(self.app_config.get("shutter_speed", 1000))
            self.camera_controller.set_filename(f"{self.image_set.description}_{sample.well_row}_{sample.well_column}")
            self.camera_controller.start_capture()


        self.finish_date_time = datetime.now()
        self.status = "Complete"
        self.db.update_image_run(self.experiment)
        self.logger.info("Annealing complete")

