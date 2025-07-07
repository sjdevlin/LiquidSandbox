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

        self.illumination_controller.illumination_setup(self.app_config.get("illumination_led_number", 1),
                                                         self.app_config.get("illumination_intensity", 0.2))
        self.camera_controller.set_shutter_speed(self.app_config.get("shutter_speed", 10000))



    def run(self):
        from views import LogView
        from tkinter import messagebox

        # ask user to ensure that image is in focus before starting the run
        # create window that pauses the run until the user clicks "Continue"
        # save the z value i focus for future reference       
        self.logger.info("Please ensure that the image is in focus before starting the run.")   
        messagebox.showinfo("Important", "Have you reset the X and Y co-ords to the origin?")  
        messagebox.showinfo("Focus Check", "Please go to first well and ensure that the image is in focus and enable autofocus before starting the run.")  
        self.focus_position = self.focus_controller.get_z()  # Get the current Z position as a reference for focus


       # First create the image run in the database, then retrieve it.  
        # This ensures that the image run is created before we start the imaging process.

        number_prev_runs_of_exp_set = self.db.get_number_image_runs_by_exp_and_set(self.experiment.id, self.image_set.id)

        self.image_run_id = self.db.add_image_run(ImageRun(
            image_set_id=self.image_set.id,
            experiment_id=self.experiment.id,
            description= (f"{self.image_set.description}_run_{number_prev_runs_of_exp_set + 1}"),
            notes=(f"Experiment: {self.experiment.description}\nImage Set: {self.image_set.description}"),
            image_set_start_date_time= datetime.now(),
            image_set_status="Not Started",
        ))

        self.image_run = self.db.get_image_run_by_id(self.image_run_id)

        # Iterate through each sample in the experiment
        self.logger.info(f"Started imaging run for experiment {self.experiment.id} with image set {self.image_set.id}")

        #home the stage before starting the imaging run
        #self._home_stage()

        self.focus_controller.autofocus(False)  # Ensure autofocus is off before homing
        self.focus_controller.move_z(self.focus_position - 100)  #TODO change to config value

        for sample in self.experiment.sample:

            self.logger.info(f"Processing sample {sample.id} at well ({sample.well_row}, {sample.well_column})")                

            for site_number in range(self.image_set.number_of_sites):

                self._move_stage_to_site(sample, site_number)
                self.focus_controller.move_z(self.focus_position)  # Return to last focus

                # Take the Z Stack
                self.logger.info(f"Capturing Z Stack for sample {sample.id} at well ({sample.well_row}, {sample.well_column})")
                self.focus_controller.autofocus(True)  # Enable autofocus to get in position then disable it
                self.focus_controller.autofocus(False)  # Disable autofocus after getting in position
                self.focus_position = self.focus_controller.get_z()  # Get the current Z position as a reference for focus

                for stack_number in range(self.image_set.stack_size):
                    self._take_image(sample, site_number, stack_number)
                self.focus_controller.move_z(self.focus_position)  # Return to original focus position after stack

            self.focus_controller.move_z(self.focus_position - 100)  # Drop Z for next major move



        self.finish_date_time = datetime.now()
        self.status = "Complete"
        self.db.update_image_run(self.experiment)
        self.logger.info("Imaging complete")

    def _home_stage(self):
        self.logger.info("Homing the stage before starting the imaging run")
        self.focus_controller.autofocus(False)  # Ensure autofocus is off before homing
        self.focus_controller.move_z(self.focus_position - 100)  #TODO change to config value
        self.stage_controller.move(axis="x", position=0, speed=self.app_config.get("max_stage_speed", 1000)) #TODO save config value in object
        self.stage_controller.move(axis="y", position=0, speed=self.app_config.get("max_stage_speed", 1000))
        self.stage_controller.reset(axis="x")
        self.stage_controller.reset(axis="y")
        self.logger.info("Stage homed successfully")


    def _move_stage_to_site(self, sample, site_number):

        x = self.plate.centre_first_well_offset_x + (sample.well_column - 1) * self.plate.well_spacing_x
        x = x + (site_number * (self.plate.well_dimension * random.uniform(0.1, 0.4))) 
        y = self.plate.centre_first_well_offset_y + (sample.well_row - 1) * self.plate.well_spacing_y
        y = y + (site_number * (self.plate.well_dimension * random.uniform(0.1, 0.4)))

        self.stage_controller.move(position = x, axis= "x", speed="normal")
        self.stage_controller.move(position = y, axis="y", speed="normal")
        sleep(1)  # Allow time for the stage to stabilize
    
    def _take_image(self, sample, site_number, stack_number):
        self.logger.info(f"Taking image for sample {sample.id} at well ({sample.well_row}, {sample.well_column}), site {site_number}, stack {stack_number}")
        new_z = self.focus_controller.get_z() + (stack_number * self.image_set.stack_step_size)
        self.focus_controller.move_z(new_z, speed="normal")  # Move to the new Z position for the stack
        filename = f"{self.image_run.id}_{sample.well_row}_{sample.well_column}_{site_number}_{stack_number}"
        self.camera_controller.set_filename(filename)
        self.camera_controller.capture_image()
        new_image = Image(
            sample_id=sample.id,
            image_run_id=self.image_run.id,
            image_dimension_x=self.camera_controller.image_dimension_x,
            image_dimension_y=self.camera_controller.image_dimension_y,
            image_file_path=filename,
            image_timestamp=datetime.now(),
            average_droplet_size=0.0,  # Placeholder, to be calculated later
            standard_deviation_droplet_size=0.0  # Placeholder, to be calculated later
            )

        # Save the image to the database
        self.db.add_image(new_image)
        self.logger.info(f"Image saved for sample {sample.id}, site {site_number}, stack {stack_number}")
