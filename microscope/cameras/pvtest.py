from microscope.cameras import pvcam
import ctypes



pvcam._pvcam_init()
cam = pvcam.PVCamera()
cam.initialize()
print(cam.settings['CHIP_NAME']['get']())
#print(cam.describe_settings())
#print(cam.get_all_settings())
print cam._get_param(pvcam.PARAM_EXP_TIME)
print cam._get_param_values(pvcam.PARAM_EXP_TIME)
pvcam._exp_abort(cam.handle, pvcam.CCS_CLEAR_CLOSE_SHTR)
# pvcam._set_param(
#     cam.handle,
#     pvcam.PARAM_PMODE,
#     ctypes.byref(ctypes.c_void_p(pvcam.PMODE_NORMAL))
# )
cam._set_param(pvcam.PARAM_PMODE, pvcam.PMODE_NORMAL)
print cam._get_param(pvcam.PARAM_PMODE), pvcam.PMODE_NORMAL
# pvcam._set_param(
#     cam.handle,
#     pvcam.PARAM_PMODE,
#     ctypes.byref(ctypes.c_void_p(pvcam.PMODE_FT))
# )
cam._set_param(pvcam.PARAM_PMODE, pvcam.PMODE_FT)
print cam._get_param(pvcam.PARAM_PMODE), pvcam.PMODE_FT
print cam._get_param_values(pvcam.PARAM_PMODE)
pvcam._set_param(
    cam.handle,
    pvcam.PARAM_PMODE,
    ctypes.byref(ctypes.c_void_p(5))
)
print cam._get_param(pvcam.PARAM_PMODE), pvcam.PMODE_FT


enums = [s for s in cam.settings.items() if s[1]['type'] == 'enum']
for enum in enums:
    if not enum[1]['readonly']:
        print enum[0], cam.describe_setting(enum[0])['values']

#print (pvcam._set_param(
#    cam.handle,
#    pvcam.PARAM_EXPOSURE_MODE,
#    ctypes.byref(ctypes.c_uint32(1))
#))
# print (_set_param(cam.handle, PARAM_EXP_TIME, ctypes.cast(ctypes.byref(ctypes.c_uint16(100)), ctypes.c_void_p)))
# print (cam._get_param(PARAM_EXP_TIME))
# print (cam._get_param(PARAM_EXPOSURE_TIME))
# print (cam._get_param(PARAM_EXPOSURE_MODE))