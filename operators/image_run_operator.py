from hardware import CameraControllerFactory, StageControllerFactory, IlluminationControllerFactory, FocusControllerFactory
from datetime import datetime
from services import Logger, AppConfig
from models import Experiment, Sample, ImageSet, ImageRun, Image
from time import sleep
import random

class ImageRunOperator:
    def __init__(self, experiment, image_set, db):
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
        from views import LogView
#        import threading
        from tkinter import messagebox

        self.start_date_time = datetime.now()
        self.status = "Not Started"

        # ask user to ensure that image is in focus before starting the run
        self.logger.info("Please ensure that the image is in focus before starting the run.")   
        # create window that pauses the run until the user clicks "Continue"
        messagebox.showinfo("Focus Check", "Please ensure that the image is in focus before starting the run. Click 'Continue' to proceed.")  
        
        log_window = LogView(self.view.root_window, self.logger.log_file)
        self.focus_controller.autofocus(True)  # Ensure autofocus is off before starting the run

       # First create the image run in the database, then retrieve it.  
        # This ensures that the image run is created before we start the imaging process.
        self.db.add_image_run(ImageRun(
            image_set_id=self.image_set.id,
            experiment_id=self.experiment.id,
            description= self.image_set.description,
            notes=(f"Experiment: {self.experiment.description}\nImage Set: {self.image_set.description}")
            image_set_start_date_time=self.start_date_time,
            image_set_status=self.status
        ))

        self.experiment.image_run = self.db.get_image_run_by_id(self.image_set.id, self.experiment.id)
        # Iterate through each sample in the experiment
        self.experiment.status = "Running"
        self.db.update_image_run(self.experiment)   
        self.logger.info(f"Started imaging run for experiment {self.experiment.id} with image set {self.image_set.id}")

        #home the stage before starting the imaging run
        self.logger.info("Homing the stage before starting the imaging run")
        self.camera_controller.autofocus(False)  # Ensure autofocus is off before homing
        self.stage_controller.move_x(0, self.app_config.get("stage_speed", 1000))
        self.stage_controller.move_y(0, self.app_config.get("stage_speed", 1000))
        sleep(1)  # Allow time for the stage to stabilize

        for sample in self.experiment.sample:

            self.logger.info(f"Processing sample {sample.id} at well ({sample.well_row}, {sample.well_column})")                
            #Switch off autofocus and drop z position by 1mm before moving stage
            self.focus_controller.autofocus(False)
            self.focus_controller.set_focus_position(sample.focus_position - 1000)  # Drop Z


            for site_number in range(self.image_set.number_of_sites):

                x = self.plate.centre_first_well_offset_x + (sample.well_column - 1) * self.plate.well_spacing_x
                x = x + (site_number * (self.plate.well_dimension * random.uniform(0.1, 0.4)))
                y = self.plate.centre_first_well_offset_y + (sample.well_row - 1) * self.plate.well_spacing_y
                y = y + (site_number * (self.plate.well_dimension * random.uniform(0.1, 0.4)))

                self.logger.info(f"Moving stage to well ({well.row}, {well.column} at position ({x}, {y})")
                self.stage_controller.move_x(x, self.app_config.get("stage_speed", 1000))
                self.stage_controller.move_y(y, self.app_config.get("stage_speed", 1000))
                sleep(1)  # Allow time for the stage to stabilize

                # Take the Z Stack
                self.logger.info(f"Capturing Z Stack for sample {sample.id} at well ({sample.well_row}, {sample.well_column})")
                self.illumination_controller.set_intensity(self.app_config.get("illumination_intensity", 100))
    #            self.focus_controller.set_focus_position(self.app_config.get("focus_position", 0))
                self.camera_controller.set_shutter_speed(self.app_config.get("shutter_speed", 1000))
                for stack_number in range(self.image_set.stack_size):
                    self.focus_controller.set_focus_position(sample.focus_position + stack_number * self.image_set.z_step_size)
                    self.camera_controller.set_filename(f"{self.image_set.description}_{sample.well_row}_{sample.well_column}_{site_number}_{stack_number}.jpg")
                    self.camera_controller.capture_image()


        self.finish_date_time = datetime.now()
        self.status = "Complete"
        self.db.update_image_run(self.experiment)
        self.logger.info("Imaging complete")

