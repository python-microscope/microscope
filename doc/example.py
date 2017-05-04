from microscope import clients

camera = clients.DataClient('PYRO:TestCamera@127.0.0.1:8005')
laser =  clients.Client('PYRO:TestLaser@127.0.0.1:8006')

laser.enable()
laser.set_power_mw(30)

camera.enable()
camera.set_exposure_time(0.15)

data = []

for i in range(10):
    data.append(camera.trigger_and_wait())
    print("Frame %d captured." % i)

print(data)

laser.disable()
camera.disable()
