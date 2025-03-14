from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError

class ProfileForm(FlaskForm):
    avatar = FileField('アバター画像', validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], '画像ファイル（jpg, png, jpeg, gif）のみ許可されています')
    ])
    status_message = StringField('ステータスメッセージ', validators=[
        Length(max=255, message='ステータスメッセージは255文字以内で入力してください')
    ])
    theme_preference = SelectField('テーマ設定', choices=[
        ('light', 'ライトモード'),
        ('dark', 'ダークモード'),
        ('system', 'システム設定に合わせる')
    ], default='system')
    submit = SubmitField('更新する') 