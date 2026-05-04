# DDI XML excerpts — variables representativas

Generado por `scripts/_dump_ddi_excerpts.py`. No editar a mano.

## Año 2024 (`geih_2024_ddi.xml`)

### `P3271`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V3990" name="P3271" files="F63" dcml="0" intrvl="discrete">
      <location StartPos="52" EndPos="52" width="1" RecSegNo="1"/>
      <labl>
        Cuál fue su sexo al nacer?
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <qstnLit>
          Cuál fue su sexo al nacer?
        </qstnLit>
      </qstn>
      <valrng>
        <range UNITS="REAL" min="1" max="2"/>
      </valrng>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `P6020`

_NOT FOUND in this DDI._

### `P6040`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V3991" name="P6040" files="F63" dcml="0" intrvl="contin">
      <location StartPos="53" EndPos="55" width="3" RecSegNo="1"/>
      <labl>
        ¿cuántos años cumplidos tiene...? (si es menor de 1 año, escriba 00)
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <preQTxt>
          3. ¿Cuál es la fecha de nacimiento de … ?

Año ____
        </preQTxt>
        <qstnLit>
          4. ¿Cuántos años cumplidos tiene … ?

Si es menor de 1 año, escriba 00
        </qstnLit>
        <postQTxt>
          5. ¿Cuál es el parentesco de ... con el jefe o jefa del hogar?	

a.	Jefe (a) del hogar
b.	Pareja, esposo(a), cónyuge, compañero(a)
c.	Hijo(a), hijastro(a)
d.	Nieto(a)
e.	Otro  pariente
f.	Empleado(a) del servicio doméstico y sus parientes 
g.	Pensionista
h.	Trabajador
i.	Otro no pariente
        </postQTxt>
        <ivuInstr>
          El dato a registrar es el del último cumpleaños de la persona y no el que está por cumplir. 

Esta pregunta solo se debe realizar a las personas que no declararon la fecha de nacimiento. 

Escriba la edad siempre a dos dígitos. Si se trata de menores de un año escriba 00. Para los de 99 años y más, escriba 99
        </ivuInstr>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `P6160`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V4041" name="P6160" files="F63" dcml="0" intrvl="discrete">
      <location StartPos="307" EndPos="307" width="1" RecSegNo="1"/>
      <labl>
        ¿sabe leer y escribir?
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <preQTxt>
          7. ¿En los últimos doce meses dejó de asistir al médico o no se hospitalizó, por no tener con que pagar estos servicios en la EPS o ARS?

1	Sí
2	No
9	No sabe, no informa
        </preQTxt>
        <qstnLit>
          1. ¿Sabe leer y escribir?

1	Sí
2	No
        </qstnLit>
        <postQTxt>
          2. ¿Actualmente ... asiste al preescolar, escuela, colegio o universidad?

1	Sí
2	No
        </postQTxt>
        <ivuInstr>
          Una persona sabe leer y escribir si es capaz de leer y escribir un párrafo sencillo al menos, en su idioma nativo.

Cuando la persona informa que sólo sabe firmar o escribir el nombre o algunas palabras o números, asigne X o marque la alternativa 2 (No).

Para el caso de personas que en el momento de realizar la encuesta se encuentran enfermas y les es imposible hablar, ver, escribir; pero sabían leer y escribir en el pasado, el recolector deberá registrar en esta pregunta la alternativa 1 (Si) y colocar la respectiva observación.
        </ivuInstr>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <catgry>
        <catValu>
          2
        </catValu>
        <labl>
          No
        </labl>
      </catgry>
      <catgry>
        <catValu>
          1
        </catValu>
        <labl>
          Sí
        </labl>
      </catgry>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `FEX_C18`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V4684" name="FEX_C18" files="F70" dcml="0" intrvl="contin">
      <location StartPos="31" EndPos="46" width="16" RecSegNo="1"/>
      <labl>
        FEX_C18
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <qstnLit>
          FEX_C18
        </qstnLit>
      </qstn>
      <valrng>
        <range UNITS="REAL" min="9.30292564259874" max="12062.6521798647"/>
      </valrng>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `fex_c_2011`

_NOT FOUND in this DDI._

### `OCI`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V4353" name="OCI" files="F64" dcml="0" intrvl="discrete">
      <location StartPos="1302" EndPos="1302" width="1" RecSegNo="1"/>
      <labl>
        Población ocupada
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <qstnLit>
          Población Ocupada
        </qstnLit>
      </qstn>
      <valrng>
        <range UNITS="REAL" min="1" max="1"/>
      </valrng>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <catgry>
        <catValu>
          1
        </catValu>
        <labl>
          Población ocupada
        </labl>
      </catgry>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `INGLABO`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V4354" name="INGLABO" files="F64" dcml="0" intrvl="contin">
      <location StartPos="1303" EndPos="1311" width="9" RecSegNo="1"/>
      <labl>
        Ingresos laborales
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <qstnLit>
          Ingresos Laborales
        </qstnLit>
        <ivuInstr>
          Hace referencia la variable de ingresos laborales
        </ivuInstr>
      </qstn>
      <valrng>
        <range UNITS="REAL" min="0" max="30000000"/>
      </valrng>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `AREA`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V4682" name="AREA" files="F70" intrvl="discrete">
      <location StartPos="28" EndPos="29" width="2" RecSegNo="1"/>
      <labl>
        AREA
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <varFormat type="character" schema="other"/>
    </var>
```

### `P6090`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V4029" name="P6090" files="F63" dcml="0" intrvl="discrete">
      <location StartPos="289" EndPos="289" width="1" RecSegNo="1"/>
      <labl>
        ¿... Está afiliado, es cotizante o es beneficiario de alguna entidad de seguridad social en salud?
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <preQTxt>
          6. Actualmente:

a.	No esta casado(a) y vive en pareja hace menos de dos años
b.	No esta  casado (a) y vive en pareja hace dos años o más
c.	Esta casado (a)
d.	Esta separado (a) o divorciado (a)
e.	Esta viudo (a)
f.	Esta soltero (a)
        </preQTxt>
        <qstnLit>
          1. ¿ ... está afiliado, es cotizante o es beneficiario de alguna entidad de seguridad social en salud? (Instituto de Seguros Sociales - ISS, Empresa Promotora de Salud - EPS o Administradora de Régimen Subsidiado - ARS)

1	Sí
2	No
9	No sabe, no informa
        </qstnLit>
        <postQTxt>
          2. ¿ Anteriormente estuvo ... afiliado, fue cotizante o  beneficiario de alguna entidad de seguridad social en salud? (Instituto de Seguros Sociales - ISS, Empresa Promotora de Salud - EPS o Administradora de Régimen Subsidiado - ARS)

1	Sí
2	No
9	No sabe, no informa
        </postQTxt>
        <ivuInstr>
          Esta pregunta busca determinar si los miembros del hogar tienen garantizada la prestación de servicios de salud por alguna institución o entidad del sistema de seguridad social en salud, bien sea en calidad de cotizante (aportante) o de beneficiario.

Si la respuesta a esta pregunta es la opción 1(SI) pase a la pregunta 4(P6100) del capítulo F. SEGURIDAD SOCIAL EN SALUD.
Si la respuesta a esta pregunta es la opción 9(No sabe, no informa) pase a la pregunta 7(P6125) del capítulo F. SEGURIDAD SOCIAL EN SALUD.
Si la respuesta es a esta pregunta es la opción 2 (NO) continúe.

-	Si la persona manifiesta estar afiliada como cotizante o beneficiaria a más de una entidad de seguridad social en salud, refiérase a la afiliación como cotizante.

-	Las madres comunitarias del ICBF son afiliadas por el ICBF al régimen contributivo y si la encuesta SISBEN las clasifica como beneficiarias de programas sociales, su núcleo familiar es afiliado al régimen subsidiado y las madres comunitarias quedarían registradas como cotizantes.

-	No se incluyen como afiliados al Sistema de Seguridad Social en Salud, las personas vinculadas al sistema, es decir aquellas que por falta de capacidad de pago y mientras logran ser beneficiarios del régimen subsidiado tienen derecho a los servicios de atención en salud que prestan las instituciones públicas (red hospitalaria pública) y aquellas privadas que tengan contrato con el Estado. Esta asegurada la atención en salud a un cotizante que se encuentra retrazado en el pago de aportes, por lo menos el mes posterior al mes en el que se realiza el pago. Una persona que se retrasa en el pago de los aportes a salud, tiene derecho a ser atendida por la entidad prestadora de los servicios de salud por un determinado tiempo, lo que significa que si en el mes de referencia la persona no a cotizado a salud lo mas seguro es que esta aun continúe afiliada al sistema de seguridad social en salud. Son ejemplos de personas vinculadas, quienes reporten que tienen carné y atención en un determinado hospital.

-	Para el correcto diligenciamiento de ésta y las preguntas subsiguientes, debe solicitarse el carné de afiliación.

-	Cuando la persona manifiesta estar afiliada a una entidad cuyo nombre no es familiar para el recolector, y por tanto existe duda de la afiliación a la seguridad social en salud, el recolector deberá solicitar el carné, marcar alternativa 1 y escribir el nombre de la entidad en observaciones.

-	Así mismo en campo usted puede encontrar otras situaciones no contempladas en la ley como ocupados no afiliados, afiliados al régimen subsidiado o afiliados como beneficiarios, aunque son prácticas no contempladas por la ley, el recolector respetará la información suministrada por el informante
        </ivuInstr>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <txt>
        Cotizantes. Son las personas que pagan por la afiliación y por consiguiente se les descuenta mensualmente de su salario. En el caso de los trabajadores independientes se establece un ingreso base de cotización sobre el cual se realizan los aportes mensuales.

Beneficiarios. Son todas las personas que quedan cubiertas por la cotización realizada por un miembro de la familia con capacidad de pago. Dentro de éstas se incluyen el (o la) cónyuge o el (o la) compañero(a) permanente del afiliado, cuya unión sea superior a dos años; los hijos menores de 18 años de cualquiera de los cónyuges que hagan parte del núcleo familiar y dependan económicamente del afiliado, los hijos mayores de 18 años con discapacidad permanente o aquellos que tengan menos de 25 años, sean estudiantes con dedicación exclusiva y dependan económicamente del afiliado. A falta de cónyuge, compañero(a) permanente e hijos con derecho, la cobertura familiar podrá extenderse a los padres del afiliado no pensionado que dependan económicamente de éste.

Son entidades de seguridad social en salud, todas aquellas entidades oficiales, mixtas, privadas, comunitarias y solidarias, organizadas para la administración de los recursos y la prestación de los servicios de salud a sus afiliados (cotizantes y beneficiarios), tales como las Entidades Promotoras de Salud (EPS), Administradoras del Régimen Subsidiado – ARS – (Cajas de Previsión o Compensación, Empresas Solidarias, etc.)

Regímenes Especiales o Entidades excluidas: El Sistema Integral de Seguridad Social en Salud no se aplica a los miembros de las Fuerzas Militares y de la Policía Nacional, a los afiliados al Fondo Nacional de Prestaciones Sociales del Magisterio y a servidores públicos de la Empresa Colombiana de Petróleos, ECOPETROL. Por situaciones jurisdiccionales, las universidades se convirtieron en régimen especial en el año 2001.  Sin embargo las empresas y servidores públicos de que trata esta excepción, quedan obligados a efectuar los aportes de solidaridad del 1% de su salario al Fosyga, en los regímenes de salud y pensiones, por esta razón a estas entidades se les considera excluidas del Sistema Integral de Seguridad Social en Salud, y pertenecen al Régimen Contributivo de Salud y deben traer diligenciada la alternativa 1.

Empresa Promotora de Salud (E.P.S.). Son las entidades responsables de la afiliación, del registro de los afiliados y del recaudo de sus cotizaciones. Son responsables de organizar y prestar, directa o indirectamente, los servicios de salud incluidos en el Plan Obligatorio de Salud, los Planes Complementarios y algunas actividades del Plan de Atención Básica. Ejemplo: el Instituto de SegurosSociales (ISS), Salud Colmena, Saludcoop, etc.

Tenga en cuenta: La NUEVA EPS es una Sociedad Anónima de carácter privado, que surge como entidad promotora de salud del régimen contributivo a través de la Resolución No. 371 del 3 de abril de 2008 de la Superintendencia Nacional de Salud, como respuesta al informe del COMPES sobre la situación de la EPS del Instituto de Seguros Sociales (ISS). La conformación y puesta en marcha de la NUEVA EPS, tiene por fin garantizar la continuidad en la prestación de los beneficios del Plan Obligatorio de Salud a nivel nacional, para la población que estando afiliada a la EPS del Instituto de Seguros Sociales (ISS) pasará de forma automática a la NUEVA EPS.

Administradoras del Régimen Subsidiado (A.R.S.). Entidades responsables de la afiliación, el registro de los afiliados y la prestación de servicios de salud a las personas del régimen subsidiado. Se cuentan como ARS: algunas EPS (Saludcoop y otras), las Cajas de Compensación Familiar y las Empresas Solidarias de Salud (ESS).

Empresa Solidaria de Salud (E.S.S). Son empresas conformadas por la comunidad o por organizaciones no gubernamentales (ONG) para administrar los recursos del régimen subsidiado. Su funcionamiento es similar al de las EPS y al igual que ellas pueden prestar directa o indirectamente los servicios de salud. 

Caja de Previsión. Son aquellas instituciones de previsión social del sector público que pertenecían al antiguo Sistema Nacional de Salud y que prestan servicios de salud a sus afiliados. Algunas instituciones de previsión han sido adaptadas al nuevo sistema y continúan funcionando como Cajas de Previsión para atender a sus clientelas particulares, por tanto se asimilan a EPS que administran el régimen contributivo. Ejemplo: Caja de Previsión de la Universidad Nacional.

Caja de Compensación Familiar. Son entidades que tienen como objetivo promover la solidaridad social entre patronos y trabajadores a través del subsidio familiar en dinero y la prestación de servicios sociales. Las Cajas de Compensación Familiar que en este momento prestan servicios de salud a sus afiliados, lo hacen mediante la transformación que ha tenido su área de salud en EPS, o en Instituciones Prestadoras de Servicios de Salud (IPS). Mediante este esquema la Caja de Compensación sería una EPS más del sistema (ejemplo: Compensar). Existen además, algunas Cajas de Compensación que sin necesidad de transformarse en EPS, han solicitado autorización para manejar los recursos del Régimen Subsidiado.
      </txt>
      <catgry>
        <catValu>
          9
        </catValu>
        <labl>
          No sabe, no informa
        </labl>
      </catgry>
      <catgry>
        <catValu>
          2
        </catValu>
        <labl>
          No
        </labl>
      </catgry>
      <catgry>
        <catValu>
          1
        </catValu>
        <labl>
          Sí
        </labl>
      </catgry>
      <varFormat type="numeric" schema="other"/>
    </var>
```

## Año 2018 (`geih_2018_ddi.xml`)

### `P3271`

_NOT FOUND in this DDI._

### `P6020`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V14244" name="P6020" files="F273" dcml="0" intrvl="discrete">
      <location StartPos="16" EndPos="16" width="1" RecSegNo="1"/>
      <labl>
        Sexo
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <preQTxt>
          1. Número de orden de la persona que proporciona la información
        </preQTxt>
        <qstnLit>
          2. Sexo

1	Hombre
2	Mujer
        </qstnLit>
        <postQTxt>
          3. ¿Cuál es la fecha de nacimiento de … ?

1	Si responde
2	No responde
        </postQTxt>
        <ivuInstr>
          Se debe tener cuidado al registrar el sexo de la persona porque hay nombres que se utilizan indistintamente para ambos sexos. Ejemplo: Concepción, Dolores, etc. Si hay duda pregunte.
        </ivuInstr>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional; va dirigida a todos los hogares encontrados en la vivienda y a todas las personas que forman parte del hogar.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <catgry>
        <catValu>
          2
        </catValu>
        <labl>
          Mujer
        </labl>
      </catgry>
      <catgry>
        <catValu>
          1
        </catValu>
        <labl>
          Hombre
        </labl>
      </catgry>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `P6040`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V14247" name="P6040" files="F273" dcml="0" intrvl="contin">
      <location StartPos="23" EndPos="25" width="3" RecSegNo="1"/>
      <labl>
        ¿cuántos años cumplidos tiene...? (si es menor de 1 año, escriba 00)
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <preQTxt>
          3. ¿Cuál es la fecha de nacimiento de … ?

Año ____
        </preQTxt>
        <qstnLit>
          4. ¿Cuántos años cumplidos tiene … ?

Si es menor de 1 año, escriba 00
        </qstnLit>
        <postQTxt>
          5. ¿Cuál es el parentesco de ... con el jefe o jefa del hogar?	

a.	Jefe (a) del hogar
b.	Pareja, esposo(a), cónyuge, compañero(a)
c.	Hijo(a), hijastro(a)
d.	Nieto(a)
e.	Otro  pariente
f.	Empleado(a) del servicio doméstico y sus parientes 
g.	Pensionista
h.	Trabajador
i.	Otro no pariente
        </postQTxt>
        <ivuInstr>
          El dato a registrar es el del último cumpleaños de la persona y no el que está por cumplir. 

Esta pregunta solo se debe realizar a las personas que no declararon la fecha de nacimiento. 

Escriba la edad siempre a dos dígitos. Si se trata de menores de un año escriba 00. Para los de 99 años y más, escriba 99
        </ivuInstr>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional; va dirigida a todos los hogares encontrados en la vivienda y a todas las personas que forman parte del hogar.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `P6160`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V14263" name="P6160" files="F273" dcml="0" intrvl="discrete">
      <location StartPos="51" EndPos="51" width="1" RecSegNo="1"/>
      <labl>
        ¿sabe leer y escribir?
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <preQTxt>
          7. ¿En los últimos doce meses dejó de asistir al médico o no se hospitalizó, por no tener con que pagar estos servicios en la EPS o ARS?

1	Sí
2	No
9	No sabe, no informa
        </preQTxt>
        <qstnLit>
          1. ¿Sabe leer y escribir?

1	Sí
2	No
        </qstnLit>
        <postQTxt>
          2. ¿Actualmente ... asiste al preescolar, escuela, colegio o universidad?

1	Sí
2	No
        </postQTxt>
        <ivuInstr>
          Una persona sabe leer y escribir si es capaz de leer y escribir un párrafo sencillo al menos, en su idioma nativo.

Cuando la persona informa que sólo sabe firmar o escribir el nombre o algunas palabras o números, asigne X o marque la alternativa 2 (No).

Para el caso de personas que en el momento de realizar la encuesta se encuentran enfermas y les es imposible hablar, ver, escribir; pero sabían leer y escribir en el pasado, el recolector deberá registrar en esta pregunta la alternativa 1 (Si) y colocar la respectiva observación.
        </ivuInstr>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional; va dirigida a todos los hogares encontrados en la vivienda y solamente para personas personas de 3 años y más.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <catgry>
        <catValu>
          2
        </catValu>
        <labl>
          No
        </labl>
      </catgry>
      <catgry>
        <catValu>
          1
        </catValu>
        <labl>
          Sí
        </labl>
      </catgry>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `FEX_C18`

_NOT FOUND in this DDI._

### `fex_c_2011`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V14609" name="fex_c_2011" files="F279" dcml="0" intrvl="contin">
      <location StartPos="217" EndPos="232" width="16" RecSegNo="1"/>
      <labl>
        Factor de expansión
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <qstnLit>
          Factor de expansión
        </qstnLit>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `OCI`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V14458" name="OCI" files="F275" dcml="0" intrvl="discrete">
      <location StartPos="968" EndPos="968" width="1" RecSegNo="1"/>
      <labl>
        Población ocupada
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <qstnLit>
          Población Ocupada
        </qstnLit>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <catgry>
        <catValu>
          1
        </catValu>
        <labl>
          Población ocupada
        </labl>
      </catgry>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `INGLABO`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V14463" name="INGLABO" files="F275" dcml="0" intrvl="contin">
      <location StartPos="981" EndPos="988" width="8" RecSegNo="1"/>
      <labl>
        Ingresos laborales
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <qstnLit>
          Ingresos Laborales
        </qstnLit>
        <ivuInstr>
          Hace referencia la variable de ingresos laborales
        </ivuInstr>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <varFormat type="numeric" schema="other"/>
    </var>
```

### `AREA`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V14513" name="AREA" files="F277" intrvl="discrete">
      <location StartPos="14" EndPos="14" width="1" RecSegNo="1"/>
      <labl>
        AREA
      </labl>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <varFormat type="character" schema="other"/>
    </var>
```

### `P6090`

```xml
<var xmlns="http://www.icpsr.umich.edu/DDI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="V14256" name="P6090" files="F273" dcml="0" intrvl="discrete">
      <location StartPos="37" EndPos="37" width="1" RecSegNo="1"/>
      <labl>
        ¿... Está afiliado, es cotizante o es beneficiario de alguna entidad de seguridad social en salud?
      </labl>
      <security>
        El acceso a microdatos y Mam-up se considera como de tratamiento especial respecto a la reserva estadística por tanto estará sujeto a la reglamentación que para el efecto defina el Comité de Aseguramiento de la reserva estadística. Resolución 173 de 2008.
      </security>
      <respUnit>
        La encuesta utiliza informante directo para las personas de 18 años y más, y para aquellas de 10 a 17 años que trabajen o estén buscando trabajo. Para los demás se acepta informante idóneo (persona del hogar mayor de 18 años, que a falta del informante directo pueda responder correctamente las preguntas). No se acepta información de empleados del servicio doméstico, pensionistas, vecinos o menores, excepto cuando el menor de edad es el jefe del hogar o cónyuge.
      </respUnit>
      <qstn>
        <preQTxt>
          6. Actualmente:

a.	No esta casado(a) y vive en pareja hace menos de dos años
b.	No esta  casado (a) y vive en pareja hace dos años o más
c.	Esta casado (a)
d.	Esta separado (a) o divorciado (a)
e.	Esta viudo (a)
f.	Esta soltero (a)
        </preQTxt>
        <qstnLit>
          1. ¿ ... está afiliado, es cotizante o es beneficiario de alguna entidad de seguridad social en salud? (Instituto de Seguros Sociales - ISS, Empresa Promotora de Salud - EPS o Administradora de Régimen Subsidiado - ARS)

1	Sí
2	No
9	No sabe, no informa
        </qstnLit>
        <postQTxt>
          2. ¿ Anteriormente estuvo ... afiliado, fue cotizante o  beneficiario de alguna entidad de seguridad social en salud? (Instituto de Seguros Sociales - ISS, Empresa Promotora de Salud - EPS o Administradora de Régimen Subsidiado - ARS)

1	Sí
2	No
9	No sabe, no informa
        </postQTxt>
        <ivuInstr>
          Esta pregunta busca determinar si los miembros del hogar tienen garantizada la prestación de servicios de salud por alguna institución o entidad del sistema de seguridad social en salud, bien sea en calidad de cotizante (aportante) o de beneficiario.

Si la respuesta a esta pregunta es la opción 1(SI) pase a la pregunta 4(P6100) del capítulo F. SEGURIDAD SOCIAL EN SALUD.
Si la respuesta a esta pregunta es la opción 9(No sabe, no informa) pase a la pregunta 7(P6125) del capítulo F. SEGURIDAD SOCIAL EN SALUD.
Si la respuesta es a esta pregunta es la opción 2 (NO) continúe.

-	Si la persona manifiesta estar afiliada como cotizante o beneficiaria a más de una entidad de seguridad social en salud, refiérase a la afiliación como cotizante.

-	Las madres comunitarias del ICBF son afiliadas por el ICBF al régimen contributivo y si la encuesta SISBEN las clasifica como beneficiarias de programas sociales, su núcleo familiar es afiliado al régimen subsidiado y las madres comunitarias quedarían registradas como cotizantes.

-	No se incluyen como afiliados al Sistema de Seguridad Social en Salud, las personas vinculadas al sistema, es decir aquellas que por falta de capacidad de pago y mientras logran ser beneficiarios del régimen subsidiado tienen derecho a los servicios de atención en salud que prestan las instituciones públicas (red hospitalaria pública) y aquellas privadas que tengan contrato con el Estado. Esta asegurada la atención en salud a un cotizante que se encuentra retrazado en el pago de aportes, por lo menos el mes posterior al mes en el que se realiza el pago. Una persona que se retrasa en el pago de los aportes a salud, tiene derecho a ser atendida por la entidad prestadora de los servicios de salud por un determinado tiempo, lo que significa que si en el mes de referencia la persona no a cotizado a salud lo mas seguro es que esta aun continúe afiliada al sistema de seguridad social en salud. Son ejemplos de personas vinculadas, quienes reporten que tienen carné y atención en un determinado hospital.

-	Para el correcto diligenciamiento de ésta y las preguntas subsiguientes, debe solicitarse el carné de afiliación.

-	Cuando la persona manifiesta estar afiliada a una entidad cuyo nombre no es familiar para el recolector, y por tanto existe duda de la afiliación a la seguridad social en salud, el recolector deberá solicitar el carné, marcar alternativa 1 y escribir el nombre de la entidad en observaciones.

-	Así mismo en campo usted puede encontrar otras situaciones no contempladas en la ley como ocupados no afiliados, afiliados al régimen subsidiado o afiliados como beneficiarios, aunque son prácticas no contempladas por la ley, el recolector respetará la información suministrada por el informante
        </ivuInstr>
      </qstn>
      <universe clusion="I">
        El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional; va dirigida a todos los hogares encontrados en la vivienda y a todas las personas que forman parte del hogar.
      </universe>
      <sumStat type="vald">
        0
      </sumStat>
      <sumStat type="invd">
        0
      </sumStat>
      <txt>
        Cotizantes. Son las personas que pagan por la afiliación y por consiguiente se les descuenta mensualmente de su salario. En el caso de los trabajadores independientes se establece un ingreso base de cotización sobre el cual se realizan los aportes mensuales.

Beneficiarios. Son todas las personas que quedan cubiertas por la cotización realizada por un miembro de la familia con capacidad de pago. Dentro de éstas se incluyen el (o la) cónyuge o el (o la) compañero(a) permanente del afiliado, cuya unión sea superior a dos años; los hijos menores de 18 años de cualquiera de los cónyuges que hagan parte del núcleo familiar y dependan económicamente del afiliado, los hijos mayores de 18 años con discapacidad permanente o aquellos que tengan menos de 25 años, sean estudiantes con dedicación exclusiva y dependan económicamente del afiliado. A falta de cónyuge, compañero(a) permanente e hijos con derecho, la cobertura familiar podrá extenderse a los padres del afiliado no pensionado que dependan económicamente de éste.

Son entidades de seguridad social en salud, todas aquellas entidades oficiales, mixtas, privadas, comunitarias y solidarias, organizadas para la administración de los recursos y la prestación de los servicios de salud a sus afiliados (cotizantes y beneficiarios), tales como las Entidades Promotoras de Salud (EPS), Administradoras del Régimen Subsidiado – ARS – (Cajas de Previsión o Compensación, Empresas Solidarias, etc.)

Regímenes Especiales o Entidades excluidas: El Sistema Integral de Seguridad Social en Salud no se aplica a los miembros de las Fuerzas Militares y de la Policía Nacional, a los afiliados al Fondo Nacional de Prestaciones Sociales del Magisterio y a servidores públicos de la Empresa Colombiana de Petróleos, ECOPETROL. Por situaciones jurisdiccionales, las universidades se convirtieron en régimen especial en el año 2001.  Sin embargo las empresas y servidores públicos de que trata esta excepción, quedan obligados a efectuar los aportes de solidaridad del 1% de su salario al Fosyga, en los regímenes de salud y pensiones, por esta razón a estas entidades se les considera excluidas del Sistema Integral de Seguridad Social en Salud, y pertenecen al Régimen Contributivo de Salud y deben traer diligenciada la alternativa 1.

Empresa Promotora de Salud (E.P.S.). Son las entidades responsables de la afiliación, del registro de los afiliados y del recaudo de sus cotizaciones. Son responsables de organizar y prestar, directa o indirectamente, los servicios de salud incluidos en el Plan Obligatorio de Salud, los Planes Complementarios y algunas actividades del Plan de Atención Básica. Ejemplo: el Instituto de SegurosSociales (ISS), Salud Colmena, Saludcoop, etc.

Tenga en cuenta: La NUEVA EPS es una Sociedad Anónima de carácter privado, que surge como entidad promotora de salud del régimen contributivo a través de la Resolución No. 371 del 3 de abril de 2008 de la Superintendencia Nacional de Salud, como respuesta al informe del COMPES sobre la situación de la EPS del Instituto de Seguros Sociales (ISS). La conformación y puesta en marcha de la NUEVA EPS, tiene por fin garantizar la continuidad en la prestación de los beneficios del Plan Obligatorio de Salud a nivel nacional, para la población que estando afiliada a la EPS del Instituto de Seguros Sociales (ISS) pasará de forma automática a la NUEVA EPS.

Administradoras del Régimen Subsidiado (A.R.S.). Entidades responsables de la afiliación, el registro de los afiliados y la prestación de servicios de salud a las personas del régimen subsidiado. Se cuentan como ARS: algunas EPS (Saludcoop y otras), las Cajas de Compensación Familiar y las Empresas Solidarias de Salud (ESS).

Empresa Solidaria de Salud (E.S.S). Son empresas conformadas por la comunidad o por organizaciones no gubernamentales (ONG) para administrar los recursos del régimen subsidiado. Su funcionamiento es similar al de las EPS y al igual que ellas pueden prestar directa o indirectamente los servicios de salud. 

Caja de Previsión. Son aquellas instituciones de previsión social del sector público que pertenecían al antiguo Sistema Nacional de Salud y que prestan servicios de salud a sus afiliados. Algunas instituciones de previsión han sido adaptadas al nuevo sistema y continúan funcionando como Cajas de Previsión para atender a sus clientelas particulares, por tanto se asimilan a EPS que administran el régimen contributivo. Ejemplo: Caja de Previsión de la Universidad Nacional.

Caja de Compensación Familiar. Son entidades que tienen como objetivo promover la solidaridad social entre patronos y trabajadores a través del subsidio familiar en dinero y la prestación de servicios sociales. Las Cajas de Compensación Familiar que en este momento prestan servicios de salud a sus afiliados, lo hacen mediante la transformación que ha tenido su área de salud en EPS, o en Instituciones Prestadoras de Servicios de Salud (IPS). Mediante este esquema la Caja de Compensación sería una EPS más del sistema (ejemplo: Compensar). Existen además, algunas Cajas de Compensación que sin necesidad de transformarse en EPS, han solicitado autorización para manejar los recursos del Régimen Subsidiado.
      </txt>
      <catgry>
        <catValu>
          9
        </catValu>
        <labl>
          No sabe, no informa
        </labl>
      </catgry>
      <catgry>
        <catValu>
          2
        </catValu>
        <labl>
          No
        </labl>
      </catgry>
      <catgry>
        <catValu>
          1
        </catValu>
        <labl>
          Sí
        </labl>
      </catgry>
      <varFormat type="numeric" schema="other"/>
    </var>
```

