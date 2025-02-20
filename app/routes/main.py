from flask import Blueprint, render_template, abort

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/test-errors')
def test_errors():
    """エラー画面をテストするための一時的なルート"""
    return render_template('test_errors.html')

@bp.route('/test-404')
def test_404():
    abort(404)

@bp.route('/test-403')
def test_403():
    abort(403)

@bp.route('/test-500')
def test_500():
    # 意図的にエラーを発生させる
    raise Exception("Test 500 error") 