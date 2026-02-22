-- ADS1115 4-Channel ADC Logger for CubeOrange+
-- Reads voltage from all 4 channels of DFRobot ADS1115 over I2C and logs to CSV

-- ADS1115 Constants - Leave unchanged!
local ADS1115_REG_POINTER_CONVERT = 0x00
local ADS1115_REG_POINTER_CONFIG = 0x01 -- ADS1115 Register Addresses
local MUX_AIN0_GND = 0x0004  -- Channel 0
local MUX_AIN1_GND = 0x0005  -- Channel 1
local MUX_AIN2_GND = 0x0006  -- Channel 2
local MUX_AIN3_GND = 0x0007  -- Channel 3
local COMP_QUE_DISABLE = 0x0003 -- Comparator configuration
local GAIN_TWOTHIRDS = 0x0000 -- Gain configuration (eGAIN_TWOTHIRDS = 0, gives ±6.144V range, 1 bit = 0.1875mV)
local GAIN_COEFFICIENT = 0.1875  -- mV per bit for GAIN_TWOTHIRDS (for 0-6V signals)
local MODE_SINGLE = 0x0001  -- Single-shot mode configuration

-- Logging Code Configuration - Change with care!
local ADS1115_I2C_ADDRESS = 0x48        -- Default address (can be 0x49 dependent on ADC switch position)
local RATE_128 = 0x0004                 -- Rate configuration (128 SPS)
local ADS1115_CONVERSION_DELAY_MS = 10  -- Conversion time at 128 SPS is ~8ms, using 10ms for safety
local READINGS_COUNT = 60               -- Number of readings to log
local LOOP_DELAY_MS = 500              -- Delay between readings in milliseconds
local file_name = "ads1115_voltage_log.csv" -- Logging file name

-- Code variable initialisations - Leave unchanged!
local file
local voltage_readings = {}
local count = 0
local current_channel = 0
local channel_configured = false
local conversion_start_time = 0
local ads1115 = i2c:get_device(0, ADS1115_I2C_ADDRESS) -- I2C bus initialization
ads1115:set_retries(10)

-- Code function definitions - leave unchanged!
local function write_ads_register(reg, value)
    local high_byte = (value >> 8) & 0xFF
    local low_byte = value & 0xFF
    local write_data = string.char(reg, high_byte, low_byte) -- Write command: register address + 2 data bytes
    return ads1115:transfer(write_data, 0)
end -- Writes 16-bit value to ADS1115 register
local function read_ads_register(reg)
    local result = ads1115:transfer(string.char(reg), 2)
    if not result then
        return nil
    end -- Writes register address and read 2 bytes in one transaction
    local value = (result:byte(1) << 8) | result:byte(2) -- Converts two bytes to 16-bit signed integer
    if value > 32767 then
        value = value - 65536
    end -- Converts to signed int16
    return value
end -- Reads 16-bit value from ADS1115 register
local function configure_channel(channel)
    local mux_config
    if channel == 0 then
        mux_config = MUX_AIN0_GND
    elseif channel == 1 then
        mux_config = MUX_AIN1_GND
    elseif channel == 2 then
        mux_config = MUX_AIN2_GND
    elseif channel == 3 then
        mux_config = MUX_AIN3_GND
    else
        return false
    end
    local config = 0x8000 |  -- Start single conversion (OS bit)
                   (mux_config << 12) |  -- Multiplexer
                   (GAIN_TWOTHIRDS << 9) |  -- Gain: ±6.144V range (for 0-5V+ signals)
                   (MODE_SINGLE << 8) |  -- Single-shot mode
                   (RATE_128 << 5) |  -- 128 SPS
                   COMP_QUE_DISABLE  -- Disable comparator
    return write_ads_register(ADS1115_REG_POINTER_CONFIG, config)
end -- Configures ADS1115 for specific channel
local function check_ads1115()
    local result = read_ads_register(ADS1115_REG_POINTER_CONFIG) -- Attempts to read the config register
    return result ~= nil
end -- Checks if ADS1115 is connected

local function mV_to_angle(value_mv)
    -- Maps millivolt reading to angle in degrees (0-360 degrees for 0-5000mV input)
    local INPUT_MIN = 450.0 -- Minimum physical input in mV. Needs to be calibrated based on actual potentiometer
    local INPUT_MAX = 5000.0
    local input_range = INPUT_MAX-INPUT_MIN 
    local output_range = 360 -- Output range in degrees

    -- Perform the linear mapping
    local scaled_angle = (value_mv/ input_range) * output_range

    return scaled_angle
end

local function write_to_file()
    if not file then
        error("Could not open file")
    end
    file:write(string.format("%u, %.2f, %.2f, %.2f, %.2f, %.2f\n", 
               millis():toint(), 
               voltage_readings[1] or 0,
               mV_to_angle(voltage_readings[1]) or 0,
               voltage_readings[2] or 0, 
               voltage_readings[3] or 0, 
               voltage_readings[4] or 0))
    file:flush()
end -- Writes data to file

-- Main Code Execution - Leave unchanged!
if not check_ads1115() then
    gcs:send_text(0, "ADS1115 not detected on I2C bus!")
    error("ADS1115 not detected")
end -- Initialises ADS1115
gcs:send_text(0, "ADS1115 detected successfully")

file = io.open(file_name, "a")
if not file then
    error("Could not create file")
end -- Opens file for logging

file:write('Time [ms], Sensor0 [mV], Disconnected1 [mV], Disconnected2 [mV], Disconnected3 [mV]\n')
file:flush() -- Writes CSV header
gcs:send_text(0, "CSV file created: " .. file_name)

function update()
    if not channel_configured then
        if not configure_channel(current_channel) then
            gcs:send_text(0, string.format("Failed to configure channel %d", current_channel))
            voltage_readings[current_channel + 1] = 0
            angle_readings[current_channel + 1] = 0
        else -- Configures the current channel
            channel_configured = true
            conversion_start_time = millis()
        end
        return update, 10 -- Reschedules quickly to read the result
    else
        if millis() - conversion_start_time >= ADS1115_CONVERSION_DELAY_MS then -- Do this if enough time has passed for conversion
            local raw_value = read_ads_register(ADS1115_REG_POINTER_CONVERT)
            if raw_value then 
                voltage_readings[current_channel + 1] = raw_value * GAIN_COEFFICIENT
            else
                voltage_readings[current_channel + 1] = 0
            end -- Reads voltage or sets to 0 on error
            channel_configured = false
            current_channel = current_channel + 1
            if current_channel >= 4 then -- Do this if all 4 channels have been read
                gcs:send_text(0, string.format("ADC: %.0fmV, %.0fdegrees", 
                              voltage_readings[1] or 0,
                              mV_to_angle(voltage_readings[1]) or 0)) -- Outputs to GCS
            
            -- code with outputing all 4 channels to GCS
            --[[ if current_channel >= 4 then -- Do this if all 4 channels have been read
                gcs:send_text(0, string.format("ADC: %.0f, %.0f, %.0f, %.0f mV", 
                              voltage_readings[1] or 0,
                              voltage_readings[2] or 0,
                              voltage_readings[3] or 0,
                              voltage_readings[4] or 0)) -- Outputs to GCS ]]


                write_to_file() -- Writes to file
                count = count + 1 -- Increments counter
                if count >= READINGS_COUNT then
                    file:close()
                    gcs:send_text(0, "Logging complete. File closed.")
                    return
                end -- Stops logging after set number of readings
                current_channel = 0 -- Resets for next cycle
                return update, LOOP_DELAY_MS -- Reschedules with full loop delay
            else
                return update, 10 -- Continues reading next channel
            end
        else
            return update, 10 -- Waits a bit more for conversion
        end
    end
end -- Main update loop

return update() -- Starts the update loop
