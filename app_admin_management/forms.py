from django import forms
from app_kiberclub.models import Locations

class UploadExcelFileForm(forms.Form):
    file = forms.FileField()
    location_name = forms.ChoiceField(
        choices=[(location['location_name'], location['location_name']) for location in
                 Locations.objects.values('location_name').distinct()],
        label="Location Name"
    )
    sheet_url = forms.ChoiceField(
        choices=[(location['sheet_url'], location['sheet_url']) for location in
                 Locations.objects.values('sheet_url').distinct()],
        label="Sheet URL"
    )
    sheet_names = forms.ChoiceField(
        choices=[(location['sheet_names'], location['sheet_names']) for location in
                 Locations.objects.values('sheet_names').distinct()],
        label="Sheet Names"
    )
