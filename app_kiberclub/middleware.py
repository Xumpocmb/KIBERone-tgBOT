from django.utils.deprecation import MiddlewareMixin

class DeviceDetectionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        print(user_agent)
        print('iphone' in user_agent)
        request.is_iphone = 'iphone' in user_agent
