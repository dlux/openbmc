# Copyright 2014-present Facebook. All Rights Reserved.
#
# This program file is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program in a file named COPYING; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301 USA

DEPENDS_append = "update-rc.d-native"

FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://init_pwm.sh \
            file://setup-fan.sh \
            file://config.json \
            file://zone1.fsc \
            file://run-fscd.sh \
           "

S = "${WORKDIR}"

binfiles += "init_pwm.sh \
            "

pkgdir = "fscd"

do_install() {
  dst="${D}/usr/local/fbpackages/${pkgdir}"
  bin="${D}/usr/local/bin"
  install -d $dst
  install -d $bin
  for f in ${binfiles}; do
    install -m 755 $f ${dst}/$f
    ln -snf ../fbpackages/${pkgdir}/$f ${bin}/$f
  done
  for f in ${otherfiles}; do
    install -m 644 $f ${dst}/$f
  done
  install -d ${D}${sysconfdir}/init.d
  install -d ${D}${sysconfdir}/rcS.d
  install -d ${D}${sysconfdir}/sv
  install -d ${D}${sysconfdir}/sv/fscd
  install -d ${D}${sysconfdir}/fsc
  install -m 644 config.json ${D}${sysconfdir}/fsc-config.json
  install -m 644 zone1.fsc ${D}${sysconfdir}/fsc/zone1.fsc
  install -m 755 setup-fan.sh ${D}${sysconfdir}/init.d/setup-fan.sh
  install -m 755 run-fscd.sh ${D}${sysconfdir}/sv/fscd/run
  update-rc.d -r ${D} setup-fan.sh start 91 5 .
}

FBPACKAGEDIR = "${prefix}/local/fbpackages"

FILES_${PN} = "${FBPACKAGEDIR}/fscd ${prefix}/local/bin ${sysconfdir} "
