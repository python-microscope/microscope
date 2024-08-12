"""
A microscope interface to Thorlabs MLS203-2 stages.

https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=5360
"""
import microscope.abc


class MLS2032Stage(microscope.abc.Device):
    """
    Instantiate a Thorlabs MLS203-2 stage.
    """

    def __init__(self, config, controller=None, simulated=False):
        """Constructor method."""
        self.stage_name = config.get('name', 'XY Stage')
        self.controller = controller
        if self.controller is not None:
            self.controller.__init__(config)
        else:
            print('A controller is not present.')
            print('The stage is initialising without a controller.')
        self.simulated = simulated
        if self.simulated:
            print('This is a simulated stage.')

    def initialise(
        self, home=True, force_home=False, max_vel=None, acc=None,
        verbose=False
    ):
        """
        Initialise the XY stage.

        Parameters
        ----------
        max_vel : float
            Maximum velocity for the stage movement.
        acc : float
            Acceleration for the stage movement.
        force_home : bool
            If True, forces the stage to home even if it's already homed.
        verbose : bool
            If True, enables verbose output during operation.
        """
        if max_vel is not None or acc is not None:
            self.set_velocity_params(
                channel=None, max_vel=max_vel, acc=acc, verbose=verbose
            )
        if self.controller:
            self.controller.standard_initialize_channels(
                self, home=home, force_home=force_home, verbose=verbose
            )

    def set_velocity_params(
        self, channel=None, max_vel=None, acc=None, verbose=False
    ):
        """
        Set the velocity and acceleration parameters of the XY stage.

        Parameters
        ----------
        channel : list or None, optional
            List of channel names or numbers. If None, sets parameters for all
            channels. Defaults to None.
        max_vel : float or None, optional
            Maximum velocity. Defaults to None.
        acc : float or None, optional
            Acceleration. Defaults to None.
        verbose : bool, optional
            Whether to print additional information. Defaults to False.
        """
        if self.controller:
            self.controller.set_velocity_params(
                self, channel, max_vel, acc, verbose
            )

    def convert_to_mm(self, value, unit):
        """
        Convert a given value from specified units to millimeters (mm).

        Parameters
        ----------
        value : float
            The value to convert.
        unit : {'um', 'mm', 'cm', 'm', 'nm', 'pm'}
            The unit of the given value.

        Returns
        -------
        float
            The value converted to millimeters (mm).

        Raises
        ------
        ValueError
            If the specified unit is not supported.
        """
        # Dictionary to map units to their conversion factor to micrometers
        unit_conversion = {
            'um': 1e-3,
            'mm': 1,
            'cm': 10,
            'm': 1e3,
            'nm': 1e-6,
            'pm': 1e-9
        }
        if unit not in unit_conversion:
            raise ValueError(
                f"Unsupported unit: {unit}. Supported units are 'um', 'mm', "
                "'cm', 'm', 'nm', 'pm'."
            )
        # Perform conversion
        converted_value = value * unit_conversion[unit]

        return converted_value

    def move(self, target_pos, relative, units='mm', verbose=False):
        """
        Move the XY stage to a specified end position.

        Parameters
        ----------
        target_pos : tuple
            A tuple specifying the target X and Y positions.
        relative : bool
            If True, the target position is relative to the current position.
        units : {'mm', 'cm', 'm', 'um', 'nm', 'pm'}, default 'mm'
            The unit of the target position.
        verbose : bool, default False
            If True, enables verbose output during the move operation.
        """
        target_mm_pos = self.convert_to_mm(target_pos, units)
        self.move_mm(target_mm_pos, relative, verbose)

    def move_mm(
        self, target_pos, channel=None, relative=False, max_vel=None, acc=None,
        permanent=False, verbose=False
    ):
        """
        Moves the XY stage to a specified end position.

        Parameters
        ----------
        target_pos : list or tuple
            A tuple specifying the target X and Y positions.
        channel : list or tuple or None, default None
            List of channel names or numbers. If None, moves all channels.
        relative : bool, default False
            If True, the movement is relative to the current position.
        max_vel : float or None, default None
            Maximum velocity for all channels.
        acc : float or None, default None
            Acceleration for all channels.
        permanent : bool, default False
            Whether to make velocity and acceleration changes permanent.
        verbose : bool, default False
            Whether to print additional information.
        """
        if self.controller:
            self.controller.moveTo(
                self, target_pos=target_pos, channel=channel,
                relative=relative, max_vel=max_vel, acc=acc,
                permanent=permanent, verbose=verbose
            )

    def home(self, force_home=False, verbose=False):
        """
        Home the XY stage.

        Parameters
        ----------
        force_home : bool
            If True, forces the stage to home regardless if it is homed
            already or not.
        verbose : bool
            If True, enables verbose output during the homing operation.
        """
        if self.controller:
            self.controller.home_channels(
                self, channel=None, force=force_home, verbose=verbose
            )

    def get_position(self):
        """
        Get the current position of the XY stage.

        Returns
        -------
        tuple
            The current X and Y position of the stage.
        """
        if self.controller:
            self.controller.get_position(self)

    def close(self, force, verbose):
        """
        Cleans up and releases resources of the XY stage.

        Parameters
        ----------
        force : bool
            If True, forces the stage to close regardless of its current state.
        verbose : bool
            If True, enables verbose output during cleanup.
        """
        # TODO: parameter `force` is unused
        if self.controller:
            self.controller.finish(self, verbose=verbose)

    def _do_shutdown(self) -> None:
        print('Shutting down the MLS203-2 stage.')


if __name__ == '__main__':
    print('Testing mls2032.py')

    config = {
        'name': 'XY Stage'
    }

    stage = MLS2032Stage(config, simulated=True)
    print(stage.stage_name)
