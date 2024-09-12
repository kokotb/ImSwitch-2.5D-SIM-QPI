from dataclasses import dataclass
@dataclass(frozen=True)
class imswitch_sim_info:
    monitorIdx: int
    """ Index of the monitor in the system list of monitors (indexing starts at
    0). """

    width: int
    """ Width of SLM, in pixels. """

    height: int
    """ Height of SLM, in pixels. """

    wavelength: int
    """ Wavelength of the laser line used with the SLM. """

    pixelSize: float
    """ Pixel size or pixel pitch of the SLM, in millimetres. """

    angleMount: float
    """ The angle of incidence and reflection of the laser line that is shaped
    by the SLM, in radians. For adding a blazed grating to create off-axis
    holography. """

    patternsDir: str
    """ Directory of .bmp images provided by Hamamatsu for flatness correction
    at various wavelengths. A combination will be chosen based on the
    wavelength. """

    isSimulation: bool

    isHamamatsuSLM: bool

    fastAPISIM_host: str

    fastAPISIM_port: str

    isFastAPISIM: bool

    nRotations: int

    nPhases: int

    simMagnefication: float
    
    isFastAPISIM: bool

    simPixelsize: float

    simNA: float

    simETA: float

    simN: float
    
    tWaitSequence: float

