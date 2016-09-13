class CameraRemote(DataRemote):
    """Adds functionality to DataRemote to support cameras.

    Applies a transform to acquired data in the processing step.
    Defines the interface for cameras.
    Must implement _fetch_data as per DataRemote._fetch_data."""
    def __init__(self):
        # A tuple defining data shape.
        self.dshape = None
        # A data type.
        self.dtype = None
        # A transform to apply to data (fliplr, flipud, rot90)
        self.dtransform = (0, 0, 0)
        super(CameraRemote, self).__init__()
        self.some_setting = 0.
        #self.settings.append()


    def _process_data(self, data):
        """Apply self.dtransform to data."""
        flips = (self.transform[0], self.transform[1])
        rot = self.transform[2]

        return {(0,0): numpy.rot90(data, rot),
                (0,1): numpy.flipud(numpy.rot90(data, rot)),
                (1,0): numpy.fliplr(numpy.rot90(data, rot)),
                (1,1): numpy.fliplr(numpy.flipud(numpy.rot90(data, rot)))
                }[flips]


    @abc.abstractmethod
    @Pyro4.expose
    def get_exposure_time(self):
        pass


    def set_some_setting(self, value):
        self.some_setting = value


    def get_some_setting(self, value):
        return self.some_setting