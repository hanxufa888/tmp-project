FROM harbor-speccheck:2.1.304-docx-xlsx-v2

COPY old/ /app/input/old/
COPY new/ /app/specification_check/check_spec/MET-C_STEER-CSTD-A0-05-A-C0/
WORKDIR /app
RUN mkdir -p specification_check/output \
    && chmod 444 input/old/*.xlsm specification_check/check_spec/*/*.xlsm \
    && sha256sum input/old/*.xlsm specification_check/check_spec/*/*.xlsm > input.sha256
