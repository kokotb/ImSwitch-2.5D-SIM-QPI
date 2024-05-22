import pyvisa as visa
import time
# Initialize PyVISA's resource manager
rm = visa.ResourceManager()

# # List available resources (instruments)
print("Available resources:")
print(rm.list_resources())

# Open a connection to the instrument
instrument = rm.open_resource('ASRLCOM4')
instrument.write_termination = '\r'
instrument.read_termination = '\n\r'
instrument.baud_rate = 19200
time.sleep(1)
instrument.clear()

# Perform a simple query
response = instrument.query('L1')

##Or perform query in 2 steps
# instrument.write('L1')
# response = instrument.read()


# Print the response
print("Response from instrument:")
print(response)

# Close the connection
instrument.close()