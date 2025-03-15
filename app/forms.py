from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError

class ProfileForm(FlaskForm):
    status_message = StringField('ステータスメッセージ', validators=[
        Length(max=255, message='ステータスメッセージは255文字以内で入力してください')
    ])
    avatar_bg_color = SelectField('アバター背景色', choices=[
        ('#1d9bf0', 'ブルー'),
        ('#ff6b6b', 'レッド'),
        ('#51cf66', 'グリーン'),
        ('#fcc419', 'イエロー'),
        ('#be4bdb', 'パープル'),
        ('#20c997', 'ティール'),
        ('#fd7e14', 'オレンジ'),
        ('#868e96', 'グレー'),
        ('#212529', 'ブラック')
    ])
    avatar_text_color = SelectField('テキスト色', choices=[
        ('#ffffff', 'ホワイト'),
        ('#000000', 'ブラック'),
        ('#f8f9fa', 'ライトグレー'),
        ('#212529', 'ダークグレー')
    ])
    submit = SubmitField('更新する') 