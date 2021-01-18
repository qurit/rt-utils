from rtutils import RTStruct

rtstruct = RTStruct('D:\Projects\Mask-to-RTStruct\sample')
rtstruct.add_roi([1,2,3,4,5,6,7,8])
print(rtstruct.ds)