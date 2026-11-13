from fastapi import FastAPI
app = FastAPI(title='Telecom API')
@app.get('/health')
def health():
 return {'status': 'ok'}
