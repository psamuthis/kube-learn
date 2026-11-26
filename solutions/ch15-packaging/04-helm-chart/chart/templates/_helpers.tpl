{{/*
Names and labels shared by every template. Define three named templates here:
  kubeapp.fullname        <release name>-<chart name>, truncated to 63 characters
  kubeapp.selectorLabels  app.kubernetes.io/name and app.kubernetes.io/instance
  kubeapp.labels          the selector labels + app.kubernetes.io/version + helm.sh/chart
*/}}
#>>
{{- define "kubeapp.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "kubeapp.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "kubeapp.labels" -}}
{{ include "kubeapp.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end }}
#<<
