from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError


class LenkaMobileController(http.Controller):

    @http.route('/lenka/app', type='http', auth='user', methods=['GET'])
    def app(self, **kwargs):
        try:
            self._service()._current_partner()
        except AccessError:
            response = request.render('lenka_financiero.mobile_app_denied', status=403)
        else:
            response = request.render('lenka_financiero.mobile_app')
        response.headers['Cache-Control'] = 'no-store, private'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'self'"
        )
        return response

    def _service(self):
        request.future_response.headers['Cache-Control'] = 'no-store, private'
        return request.env['lenka.mobile.service']

    @http.route('/lenka/mobile/v1/dashboard', type='json', auth='bearer', methods=['POST'], csrf=False)
    def dashboard(self, **kwargs):
        return self._service().get_my_dashboard()

    @http.route('/lenka/mobile/v1/operations', type='json', auth='bearer', methods=['POST'], csrf=False)
    def operations(self, **kwargs):
        return self._service().get_my_operations()

    @http.route('/lenka/mobile/v1/operations/<int:operation_id>', type='json', auth='bearer', methods=['POST'], csrf=False)
    def operation_detail(self, operation_id, **kwargs):
        return self._service().get_my_operation_detail(operation_id)

    @http.route('/lenka/mobile/v1/investments', type='json', auth='bearer', methods=['POST'], csrf=False)
    def investments(self, **kwargs):
        return self._service().get_my_investments()

    @http.route('/lenka/mobile/v1/investments/<int:investment_id>', type='json', auth='bearer', methods=['POST'], csrf=False)
    def investment_detail(self, investment_id, **kwargs):
        return self._service().get_my_investment_detail(investment_id)

    @http.route('/lenka/mobile/v1/statements', type='json', auth='bearer', methods=['POST'], csrf=False)
    def statements(self, **kwargs):
        return self._service().get_my_statements()
