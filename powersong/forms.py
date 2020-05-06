from django.forms import ModelForm
from powersong.models import Athlete

class SettingForm(ModelForm):
    class Meta:
        model = Athlete
        fields = ['share_activity_songs', 'share_activity_link', 'share_activity_songs_mode']

