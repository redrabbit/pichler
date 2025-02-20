"""
Helper module for working with Nabto communication client

More info on Nabto can be found here:
https://www.nabto.com/developer
https://downloads.nabto.com/assets/docs/TEN025 Writing a Nabto API client application.pdf
"""

import sys
import os
import json
from ctypes import *

class Client:
	"""
	Simple wrapper for Nabto client library (currently only limited session/RPC functionality)
	"""

	def __init__(self, home):
		if sys.platform == 'win32':
			library = 'nabto_client_api.dll'
		elif sys.platform == 'darwin':
			library = 'libnabto_client_api.dylib'
		else:
			library = 'libnabto_client_api.so'

		package_dir = os.path.dirname(os.path.abspath(__file__))
		self.client = cdll.LoadLibrary(os.path.join(package_dir, 'libs', library))

		# NABTO_DECL_PREFIX nabto_status_t NABTOAPI nabtoStartup(const char* nabtoHomeDir);
		self.client.nabtoStartup(home.encode())
		self.client.nabtoInstallDefaultStaticResources(None)
		self.client.nabtoSetOption(b'urlPortalHostName', b'lscontrol')

	def __del__(self):
		# NABTO_DECL_PREFIX nabto_status_t NABTOAPI nabtoShutdown(void);
		self.client.nabtoShutdown()

	def get_local_devices(self):
		"""
		Enumerate local Nabto devices
		
		Returns
		-------
		list
			Found devices
		"""
		devices = pointer(c_char_p())
		count = c_int(0)
		# NABTO_DECL_PREFIX nabto_status_t NABTOAPI nabtoget_local_devices(char*** devices, int* numberOfDevices);
		self.client.nabtoget_local_devices(pointer(devices), pointer(count))
		if (count.value != 0):
			return [devices.contents.value]

		return []

	def CreateProfile(self, user, pwd):
		"""
		Create profile that can be used to establish a session to device
		
		Parameters
		----------
		user : str
			User name of account associated with device
		pwd : str
			Password for given account
		
		Returns
		-------
		int
			Nabto status (0=success)
		"""
		# NABTO_DECL_PREFIX nabto_status_t NABTOAPI nabtoCreateProfile(const char* email, const char* password);
		return self.client.nabtoCreateProfile(user.encode(), pwd.encode())

	def open_session(self, user, pwd):
		"""
		Open session to device
		
		Parameters
		----------
		user : str
			User name of account associated with device
		pwd : str
			Password for given account
		
		Returns
		-------
		Client.Session
			Session object
		"""
		return self.Session(self.client, user, pwd)

	class Session:
		"""
		A class that represents opened session
		"""
		def __init__(self, client, user, pwd):
			self.client = client

			session = c_void_p()
			# NABTO_DECL_PREFIX nabto_status_t NABTOAPI nabtoopen_session(nabto_handle_t* session, const char* id, const char* password);
			status = self.client.nabtoOpenSession(pointer(session), user.encode(), pwd.encode())
			if status == 5:
				status = self.client.nabtoCreateProfile(user.encode(), pwd.encode())
				if status != 0:
					print('nabtoCreateProfile error (%d)' % status)

				session = c_void_p()
				status = self.client.nabtoOpenSession(pointer(session), user.encode(), pwd.encode())

			if status != 0:
				print('nabtoOpenSession error (%d)' % status)
			self.session = session

		def __del__(self):
			self.client.nabtoCloseSession(self.session)

		def rpc_set_default_interface(self, interfaceDefinition):
			"""
			Assign RPC interface definition to session
			
			Parameters
			----------
			interfaceDefinition : str
				XML with RPC interface definition
			"""
			err = c_char_p()
			# NABTO_DECL_PREFIX nabto_status_t NABTOAPI nabtoRpcSetDefaultInterface(nabto_handle_t session, const char* interfaceDefinition, char** errorMessage);
			if self.client.nabtoRpcSetDefaultInterface(self.session, interfaceDefinition.encode(), pointer(err)) != 0:
				print('nabtoRpcSetDefaultInterface error: %s' % err)

		def rpc_invoke(self, nabtoUrl):
			"""
			Invoke RPC command
			
			Parameters
			----------
			nabtoUrl : str
				URL that contains RPC command along with command parameters
			
			Returns
			-------
			dict
				RPC response
			"""
			out = c_char_p()
			self.client.nabtoRpcInvoke(self.session, nabtoUrl.encode(), pointer(out))

			if out:
				response = out.value
				self.client.nabtoFree(out)
				return json.loads(response)

			return []
