from microscope import clients

# camera = clients.DataClient('PYRO:TestCamera@127.0.0.1:8005')
# laser =  clients.Client('PYRO:TestLaser@127.0.0.1:8006')
wfs = clients.DataClient('PYRO:SID4Device@127.0.0.1:8005')

# laser.enable()
# laser.set_power_mw(30)
#
# camera.enable()
# camera.set_exposure_time(0.15)

wfs.enable()

for i in range(10):
    data = wfs.trigger_and_wait()
    print(data[0]['tilts'])

# laser.disable()
# camera.disable()
wfs.disable()
wfs.shutdown()