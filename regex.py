re.compile(
    '\[(?P<date_time>\S+ -\S+).*] (?P<ip>\S+) (?P<cn>[^\]\[]+)\t\[(?P<user_agent>[^\]]+)]\t(?P<http_version>\S+) '
    '(?P<http_method>\S+) (?P<http_status>\S+) (?P<url>\S+)\t(?P<size_bytes>\S+) bytes\t(?P<duration_ms>\S+) ms'
)
