sendEmail - Send email from a console near you!
Written by: Brandon Zehm <caspian@dotconf.net>
http://caspian.dotconf.net/
http://www.tsheets.com/

// Language: Portuguese (Brazil)
// Traduzido por: nogueira_jr@ig.com.br

-----------------
Instru‡äes de uso
-----------------

sendEmail-1.55 by Brandon Zehm <caspian@dotconf.net>

Comando:  sendEmail -f ENDERE€O [op‡äes]

  Necess rio:
    -f ENDERE€O               endere‡o de quem est  enviando o email
    * Pelo menos um destinat rio, via -t, -cc, ou -bcc
    * Corpo da mensagem, via -m, STDIN, ou -o message-file=FILE

  Comum:
    -t ENDERE€O [ENDERE€OS...] destinat rio(s)
    -u "ASSUNTO"               assunto da mensagem
    -m "MENSAGEM"              corpo da mensagem
    -s SERVER[:PORT]           servidor smtp, default e' a porta localhost:25

  Opcional:
    -a   ARQ [ARQ...]           Arquivo(s) anexado
    -cc  ENDERE€O [ENDERE€O...] cc endere‡os(s)
    -bcc ENDERE€O [ENDERE€O...] bcc endere‡o(s)
    -xu  USUARIO                nome do usuario para autentica‡Æo
    -xp  SENHA                  senha para autentica‡Æo

  Extras:
    -b BINDADDR[:PORT]        endere‡o do host local bind
    -l ARQLOG                 fazer LOG no arquivo indicado
    -v                        verbal, use v rias vezes para grandes efeitos
    -q                        silencioso (nÆo ecoa saidas)
    -o NOME=VALOR             op‡äes avan‡adas, para detalhes use: --help misc
        -o message-content-type=<auto|text|html>
        -o message-file=ARQUIVO      -o message-format=RAW
        -o message-header=HEADER     -o message-charset=CHARSET
        -o reply-to=ENDERE€O         -o timeout=SEGUNDOS
        -o username=USUARIO          -o password=SENHA
        -o tls=<auto|yes|no>         -o fqdn=FQDN

  Help:
    --help                    informa‡äes gerais (que voce le agora)
    --help addressing         detalhes de endere‡os e suas op‡äes
    --help message            detalhes do corpo da mensagem e suas op‡äes
    --help networking         detalhes -s, -b, etc
    --help output             detalhes de saidas e suas op‡äes
    --help misc               detalhes op‡Æo -o, TLS, autent SMTP auth etc



---------------
Exemplos
---------------

Simples Email:
  sendEmail -f myaddress@isp.net \
            -t nogueira_jr@ig.com.br  \
            -s relay.isp.net     \
            -u "Teste email"      \
            -m "Ola, isso e' um teste de email."

Enviando para v rias pessoas:
  sendEmail -f myaddress@isp.net \
            -t "Scott Thomas <scott@isp.net>" nogueira_jr@ig.com.br renee@isp.net \
            -s relay.isp.net     \
            -u "Teste email"      \
            -m "Ola, isso e' um teste de email."

Enviando para v rias pessoas e enviando copias cc e bcc:
(existe diferentes formas de enviar para varios destinatarios, usando TO
mas voce pode usar CC e BCC para destinatarios tambem)
  sendEmail -f myaddress@isp.net \
            -t scott@isp.net;jason@isp.net;nogueira_jr@ig.com.br  \
            -cc jennifer@isp.net paul@isp.net jeremiah@isp.net \
            -bcc troy@isp.net miranda@isp.net jay@isp.net \
            -s relay.isp.net \
            -u "Teste email com copias cc e bcc" \
            -m "Ola, isso e' um teste de email."


Enviando para v rias pessoas com v rios anexos:
  sendEmail -f myaddress@isp.net \
            -t nogueira_jr@ig.com.br \
            -cc jennifer@isp.net paul@isp.net jeremiah@isp.net \
            -s relay.isp.net \
            -u "Teste email com c¢pias cc e bcc" \
            -m "Ola, isso e' um teste de email."
            -a /mnt/storage/document.sxw "/root/My Documents/Work Schedule.kwd"


Enviando um email com o conteudo de um arquivo no corpo da mensagem:
  cat /tmp/file.txt | sendEmail -f myaddress@isp.net \
                                -t nogueira_jr@ig.com.br \
                                -s relay.isp.net \
                                -u "Ola, isso e' um teste de email com anexo."
 

Enviando um email com o conteudo de um arquivo no corpo da mensagem (m‚todo 2):
  sendEmail -f myaddress@isp.net \
            -t nogueira_jr@ig.com.br \
            -s relay.isp.net \
            -o message-file=/tmp/file.txt \
            -u "Ola, isso e' um teste de email com anexo."
 

Enviando um email HTML: (certifique-se que o arquivo tem <html> no in¡cio)
  cat /tmp/file.html | sendEmail -f myaddress@isp.net \
                                 -t nogueira_jr@ig.com.br \
                                 -s relay.isp.net \
                                 -u "Ola, isso e' um teste de email com HTML."
 


