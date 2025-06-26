from models import Experiment, Sample
from datetime import datetime
from operators import ExperimentOperator
import copy


class ExperimentListPresenter():
    def __init__(self, view, db):
        self.view = view
        self.db = db
        self.view.exp_bind_row_selection(self.on_exp_row_selected)
#        self.view.img_bind_row_selection(self.on_img_row_selected)
        self.refresh_view()
        self.view.delete_button.configure(command=self.delete_experiment)
        self.view.copy_button.configure(command=self.copy_experiment)
        self.view.edit_button.configure(command=self.open_experiment)
        self.view.new_button.configure(command=self.new_experiment)


    def on_exp_row_selected(self, event):
        """This method handles the row selection logic."""
        self.selected_row = self.view.get_id_of_selected_row()
        if self.selected_row:
            self.view.enable_run_button()
            self.view.enable_copy_button()
            if self.db.get_experiment_by_id(self.selected_row).anneal_status == "Not Run":
                self.view.enable_delete_button()
                self.view.enable_edit_button()
                self.view.run_button.configure(text="Run")
                self.view.run_button.configure(command=self.run_experiment)
                self.view.run_button.configure(fg_color='#992200')
            elif self.db.get_experiment_by_id(self.selected_row).anneal_status == "Complete" or self.db.get_experiment_by_id(self.selected_row).anneal_status == "Aborted":
                self.view.disable_delete_button()
                self.view.disable_edit_button()
                self.view.run_button.configure(text="Results")
                self.view.run_button.configure(command=self.open_experiment)
                self.view.run_button.configure(fg_color='#009922')


    def refresh_view(self):
#        self.selected_row = None
        experiments = self.db.get_all_experiments()
        image_sets = self.db.get_all_image_sets()

        # Convert SQLAlchemy objects into dictionaries or tuples
        data = [
            (
            exp.id,
            exp.description,
            exp.plate_id,
            exp.creation_date_time.strftime('%Y-%m-%d %H:%M:%S') if exp.creation_date_time else "",
            len(exp.sample) )
            for exp in experiments
        ]
        self.view.show_experiments(data)

        data = [
            (
            ims.id,
            ims.description,
            ims.lens,
            ims.stack_size)
            for ims in image_sets
        ]
        self.view.show_image_sets(data)


    def copy_experiment(self):
        old_experiment = self.db.get_experiment_by_id(self.selected_row)
        new_experiment = Experiment(plate_id = old_experiment.plate_id)
        new_experiment.description = f"{old_experiment.description} (copy)"
        new_experiment.notes = f"**copied from experiment: {old_experiment.id} ** \n{old_experiment.notes}"
        new_experiment.anneal_status = "Not Run"
        new_experiment.creation_date_time = datetime.now()
        new_experiment.sample = [Sample(experiment_id=new_experiment.id, plate_well_id=s.plate_well_id, temperature_profile_id=s.temperature_profile_id, well_index=s.well_index ) for s in old_experiment.sample]
        self.db.add_experiment(new_experiment)
        self.view.disable_run_button()
        self.view.disable_copy_button()
        self.view.disable_edit_button()
        self.view.disable_delete_button()
        self.refresh_view()

    def new_experiment(self):
        from views import ExperimentDetailView
        from presenters import ExperimentDetailPresenter
        self.view.home_frame.pack_forget()  # Hide the current view
        experiment_view = ExperimentDetailView(self.view)  # Create a new view
        experiment_presenter = ExperimentDetailPresenter(experiment_view, self.view, self.db)  # Initialize the new presenter with the root widget

    def open_experiment(self):
        from views import ExperimentDetailView
        from presenters import ExperimentDetailPresenter
        self.view.home_frame.pack_forget()  # Hide the current view
        experiment_id = self.view.get_id_of_selected_row()
        experiment_view = ExperimentDetailView(self.view)  # Create a new view
        experiment_presenter = ExperimentDetailPresenter(experiment_view, self.view, self.db, experiment_id)  # Initialize the new presenter with the root widget

    def delete_experiment(self):
        self.db.delete_experiment(self.selected_row)
        self.view.disable_run_button()
        self.view.disable_copy_button()
        self.view.disable_edit_button()
        self.view.disable_delete_button()
        self.refresh_view()

    def run_experiment(self):
        from views import LogView
        import threading

        new_experiment = ExperimentOperator(self.db.get_experiment_by_id(self.selected_row), self.db)
        
        # Since Logger is a singleton, simply create it here.
        from services import Logger
        log_file_path = Logger().log_file
        #TODO consider log window to always access singleton logger and no need to pass the reference
        
        # Create a new window to display the log file in real time.
        log_window = LogView(self.view.root_window, log_file_path)

        # Run the annealing process in a separate thread.
        def run_and_refresh():
            new_experiment.anneal()
            # After completion, schedule a refresh of the view in the main thread.
            self.view.after(0, self.refresh_view)

        thread = threading.Thread(target=run_and_refresh, daemon=True)
        thread.start()

