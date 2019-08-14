from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import Form, FieldList, FormField, IntegerField, StringField, \
        SubmitField
from wtforms import validators as wtf_validators
from wtforms.utils import unset_value
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
from itertools import chain
import itertools



app = Flask(__name__)

app.secret_key = 'TEST'
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
'sqlite:///' + os.path.join(BASEDIR, 'app.db')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

_max_nb_entries = 100
_max_len_per_entry = 30

class Crew(db.Model):
    __tablename__ = 'crew'
    id = db.Column(db.Integer, primary_key=True)
    persons = db.Column(db.String(_max_nb_entries*_max_len_per_entry),default="",nullable=False)

    def __repr__(self):
        return '<id: {}, persons: {}>'.format(self.id, self.persons)

@app.before_request
def before_request():
    db.create_all()


_delimiter = "#;_"
class FieldListFromString(FieldList):
    """
    The idea here is to have a FieldList but to store the data in a string format instead of a list
    """
    def process(self, formdata, data=unset_value):
        self.entries = []
        if data is unset_value or not data:
            try:
                data = self.default()
            except TypeError:
                data = self.default
                
        ## Modification from classic FieldList
        if data and 0<len(data):
            data = data.split(_delimiter)
        else:
            data = []
        #
            
        self.object_data = data

        if formdata:
            indices = sorted(set(self._extract_indices(self.name, formdata)))
            if self.max_entries:
                indices = indices[:self.max_entries]

            idata = iter(data)
            for index in indices:
                try:
                    obj_data = next(idata)
                except StopIteration:
                    obj_data = unset_value
                self._add_entry(formdata, obj_data, index=index)
        else:
            for obj_data in data:
                self._add_entry(formdata, obj_data)

        while len(self.entries) < self.min_entries:
            self._add_entry(formdata)


    def populate_obj(self, obj, name):
        values = getattr(obj, name, None)
        try:
            ivalues = iter(values)
        except TypeError:
            ivalues = iter([])

        candidates = itertools.chain(ivalues, itertools.repeat(None))
        _fake = type(str('_fake'), (object, ), {})
        output = []
        for field, data in zip(self.entries, candidates):
            fake_obj = _fake()
            fake_obj.data = data
            field.populate_obj(fake_obj, 'data')
            output.append(fake_obj.data)
        
        ## Modification from classic FieldList
        setattr(obj, name, _delimiter.join(output))


     
class TestForm(FlaskForm):
    persons = FieldListFromString(StringField('Persons',default='',validators=[wtf_validators.Length(min=0, max=_max_len_per_entry)]),
                                  min_entries=1, max_entries=_max_nb_entries)


@app.route('/', methods=['POST', 'GET'])
def example():
    print('request.form',request.form)
    # this paragraph is trick for testing: (merging modification and add new)
    existing_crew = Crew.query.get(1)
    if existing_crew is None: 
        crew = Crew()
    else:
        crew = existing_crew
        
    form = TestForm(obj=crew)
    
    if form.validate_on_submit():
        form.populate_obj(crew)
        
        if existing_crew is None:# this trick for testing: (merging modification and add new)
            db.session.add(crew)
            
        db.session.commit()

    return render_template('index.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)